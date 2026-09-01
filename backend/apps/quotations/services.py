import datetime
import uuid
from decimal import ROUND_HALF_UP, Decimal
from typing import Any, Dict, List, Optional

from django.db import transaction
from django.db.models import QuerySet
from rest_framework import exceptions as drf_exceptions

from apps.audit.models import AuditAction
from apps.audit.services import AuditLogService
from apps.boq.selectors import list_includible_items_for_boq
from apps.boq.services import BOQService, BOQSummaryService
from apps.common.exceptions import ConflictError
from apps.products.services import ProductService
from apps.projects.models import Project
from apps.quotations import selectors, validators
from apps.quotations.models import Quotation, QuotationItem, QuotationStatus
from apps.quotations.repositories import QuotationItemRepository, QuotationRepository

QUOTATION_AUDITED_FIELDS = (
    "project_id",
    "boq_id",
    "client_id",
    "quote_number",
    "version",
    "subtotal",
    "discount",
    "tax",
    "total",
    "terms",
    "payment_schedule",
    "valid_until",
    "status",
    "notes",
)


def _serialize_quotation_audit_value(value: Any) -> Any:
    """
    Same JSONField-has-no-custom-encoder reasoning as Project (BE-029),
    Product (BE-033), and BOQItem (BE-036) -- Quotation's audited fields
    additionally include a plain `datetime.date` (valid_until), a type none
    of those three needed to handle yet.
    """
    if isinstance(value, (datetime.date, datetime.datetime)):
        return value.isoformat()
    if isinstance(value, uuid.UUID):
        return str(value)
    if isinstance(value, Decimal):
        return str(value)
    return value


def _quotation_audit_state(quotation: Quotation) -> Dict[str, Any]:
    return {
        field: _serialize_quotation_audit_value(getattr(quotation, field))
        for field in QUOTATION_AUDITED_FIELDS
    }


def _compute_amount(quantity: Decimal, rate: Decimal) -> Decimal:
    """
    quantity * rate, explicitly quantized to 2 decimal places -- the same
    Decimal-precision discipline BOQItemService._compute_amount established
    (BE-036), duplicated here rather than imported: QuotationItem and
    BOQItem are separate models in separate apps, and the formula is the
    entirety of the function, so a cross-app import would buy no real
    reuse over a three-line duplicate.
    """
    return (Decimal(quantity) * Decimal(rate)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _ensure_latest_version(quotation: Quotation) -> None:
    """
    Shared guard for revise/send/approve/reject (BE-040/BE-041): raises
    ConflictError (409) if a newer version of this quote_number already
    exists. Acting on a stale version -- editing it, sending it, approving
    it -- would let the version chain fork or resurrect a superseded
    document, neither of which the versioning model allows.
    """
    max_version = QuotationRepository.get_max_version(quotation.company_id, quotation.quote_number)
    if quotation.version != max_version:
        raise ConflictError(
            "A newer version of this quotation already exists; only the latest version can be acted on."
        )


class QuotationService:
    """
    Business logic and orchestration service for Quotation management
    (BE-039). A Quotation is created either from a Project's BOQ (copying
    its current includible items and BOQSummaryService's computed summary
    verbatim) or manually (caller-supplied items, with discount/tax
    entered directly as flat currency amounts). `client` is always derived
    from `project.client_id`, never caller-supplied -- a Quotation's client
    is always its project's client, the same server-derived-relationship
    pattern ProjectService.create_project established for BOQ's `company`.
    """

    @classmethod
    def list_quotations_for_project(cls, project: Project, ordering: str = "-created_at") -> QuerySet[Quotation]:
        return selectors.list_quotations_for_project(project.id, ordering=ordering)

    @classmethod
    def get_quotation_by_id(
        cls,
        quotation_id: str | uuid.UUID,
        company_id: Optional[str | uuid.UUID] = None,
    ) -> Quotation:
        """
        Retrieve an active, non-deleted Quotation by primary key UUID.
        Raises NotFound if it does not exist, is soft-deleted, or belongs
        to another company.
        """
        quotation = QuotationRepository.get_by_id(quotation_id)

        if company_id is not None and str(quotation.company_id) != str(company_id):
            raise drf_exceptions.NotFound("The requested quotation was not found.")

        return quotation

    @classmethod
    def _build_items_from_boq(cls, project: Project, actor_user: Any, request: Any):
        """
        Resolve the project's own BOQ (auto-creating it if needed, the same
        BOQService.get_or_create_boq_for_project call BOQDetailView makes)
        and copy its current includible items (excludes is_optional/
        is_alternative, matching BOQSummaryService's own exclusion rule) as
        a frozen snapshot. Raises ValidationError if the BOQ has nothing to
        copy -- a quotation with zero items is not a meaningful commercial
        document.
        """
        boq = BOQService.get_or_create_boq_for_project(project, actor_user=actor_user, request=request)
        boq_items = list(list_includible_items_for_boq(boq.id))

        if not boq_items:
            raise drf_exceptions.ValidationError(
                {"items": ["The project's BOQ has no items to create a quotation from."]}
            )

        summary = BOQSummaryService.compute_summary(boq)

        item_rows = [
            QuotationItem(
                product=boq_item.product,
                description=boq_item.description,
                quantity=boq_item.quantity,
                unit=boq_item.unit,
                rate=boq_item.rate,
                amount=_compute_amount(boq_item.quantity, boq_item.rate),
            )
            for boq_item in boq_items
        ]

        return boq, item_rows, summary

    @classmethod
    def _build_items_from_input(
        cls,
        company_id: str | uuid.UUID,
        items_data: List[Dict[str, Any]],
    ):
        """
        Build QuotationItem rows from caller-supplied item data. Each item
        needs either a `product_id` (defaults description/unit/rate from
        the product, same reuse-don't-duplicate pattern
        BOQItemService.create_item established) or an explicit
        description/quantity/rate. discount/tax are NOT per-item here
        (QuotationItem has no such column) -- they are supplied at the
        Quotation level by the caller instead.
        """
        item_rows: List[QuotationItem] = []
        subtotal = Decimal("0.00")

        for raw in items_data:
            product = None
            product_id = raw.get("product_id")
            if product_id:
                # Raises NotFound if the product doesn't exist or belongs to another company.
                product = ProductService.get_product_by_id(product_id, company_id=company_id)

            description = (raw.get("description") or "").strip()
            if not description:
                if product is not None:
                    description = product.name
                else:
                    raise drf_exceptions.ValidationError(
                        {"items": ["description is required when no product is referenced."]}
                    )

            unit = raw.get("unit") or (product.unit if product is not None else "")

            rate = raw.get("rate")
            if rate is None:
                rate = product.default_selling_rate if product is not None else None
            if rate is None:
                raise drf_exceptions.ValidationError(
                    {"items": ["rate is required when no product is referenced or the product has no default selling rate."]}
                )

            quantity = validators.require_positive_quantity(raw.get("quantity"))
            amount = _compute_amount(quantity, rate)
            subtotal += amount

            item_rows.append(
                QuotationItem(
                    product=product,
                    description=description,
                    quantity=quantity,
                    unit=unit,
                    rate=rate,
                    amount=amount,
                )
            )

        return item_rows, subtotal

    @classmethod
    def create_quotation(
        cls,
        project: Project,
        items: Optional[List[Dict[str, Any]]] = None,
        discount: Any = None,
        tax: Any = None,
        terms: str = "",
        payment_schedule: Any = None,
        valid_until: Any = None,
        notes: str = "",
        actor_user: Any = None,
        request: Any = None,
    ) -> Quotation:
        """
        Create a new Quotation (version 1 of a fresh quote_number) for an
        already-authorized Project.

        - `items=None` (omitted entirely): pull the project's current BOQ
          includible items and its computed summary, both copied verbatim.
        - `items=[...]` (an explicit, possibly-empty list was supplied):
          build items manually; `discount`/`tax` are flat currency amounts
          from the request (default 0), `subtotal` is the sum of item
          amounts, `total = subtotal - discount + tax`.
        """
        with transaction.atomic():
            company = QuotationRepository.get_company_by_id(project.company_id)

            if items is None:
                boq, item_rows, summary = cls._build_items_from_boq(project, actor_user, request)
                subtotal = summary["subtotal"]
                cleaned_discount = summary["discount"]
                cleaned_tax = summary["tax"]
                total = summary["total"]
            else:
                boq = None
                item_rows, subtotal = cls._build_items_from_input(project.company_id, items)
                cleaned_discount = discount if discount is not None else Decimal("0.00")
                cleaned_tax = tax if tax is not None else Decimal("0.00")
                total = subtotal - cleaned_discount + cleaned_tax

            quote_number = QuotationRepository.next_quote_number(project.company_id)

            quotation = QuotationRepository.create(
                company=company,
                project=project,
                boq=boq,
                client=project.client,
                quote_number=quote_number,
                version=1,
                subtotal=subtotal,
                discount=cleaned_discount,
                tax=cleaned_tax,
                total=total,
                terms=terms or "",
                payment_schedule=payment_schedule if payment_schedule is not None else [],
                valid_until=valid_until,
                status=QuotationStatus.DRAFT,
                notes=notes or "",
            )

            for item_row in item_rows:
                item_row.quotation = quotation
            QuotationItemRepository.bulk_create(item_rows)

            AuditLogService.record(
                action=AuditAction.CREATE,
                entity_type="quotation",
                entity_id=quotation.id,
                company_id=company.id,
                actor_user=actor_user,
                after_state=_quotation_audit_state(quotation),
                request=request,
            )

            return quotation

    @classmethod
    def revise_quotation(
        cls,
        quotation: Quotation,
        items: Optional[List[Dict[str, Any]]] = None,
        discount: Any = None,
        tax: Any = None,
        terms: Optional[str] = None,
        payment_schedule: Any = None,
        valid_until: Any = None,
        notes: Optional[str] = None,
        actor_user: Any = None,
        request: Any = None,
    ) -> Quotation:
        """
        Create a new version of an already-authorized Quotation (BE-040),
        per CLAUDE.md's "Revision -> new version" rule -- the source row is
        never mutated, only ever read from.

        Clone-then-partial-override semantics (matching
        ProjectService.update_project's own partial-field-override style,
        applied here to a new row instead of an in-place update): any
        field omitted from this call carries over unchanged from the
        source version. `items=None` clones the source version's items
        verbatim (and its `boq`/`subtotal` along with them); an explicit
        `items` list replaces them entirely and recomputes `subtotal`
        (clearing `boq`, since the new items are no longer necessarily a
        BOQ snapshot). `discount`/`tax` follow the same carry-over-unless-
        given rule either way; `total` is always recomputed from the
        version's own final subtotal/discount/tax.

        Guard: only the latest version of a quote_number may be revised
        (Backend Lead decision, Sprint 5 planning) -- raises ConflictError
        (409) if a newer version already exists, keeping the version chain
        linear rather than allowing it to fork.
        """
        with transaction.atomic():
            _ensure_latest_version(quotation)

            if items is None:
                boq = quotation.boq
                source_items = QuotationItemRepository.all_for_quotation(quotation.id)
                item_rows = [
                    QuotationItem(
                        product=item.product,
                        description=item.description,
                        quantity=item.quantity,
                        unit=item.unit,
                        rate=item.rate,
                        amount=item.amount,
                    )
                    for item in source_items
                ]
                subtotal = quotation.subtotal
            else:
                boq = None
                item_rows, subtotal = cls._build_items_from_input(quotation.company_id, items)

            cleaned_discount = discount if discount is not None else quotation.discount
            cleaned_tax = tax if tax is not None else quotation.tax
            total = subtotal - cleaned_discount + cleaned_tax

            new_version = QuotationRepository.create(
                company=quotation.company,
                project=quotation.project,
                boq=boq,
                client=quotation.client,
                quote_number=quotation.quote_number,
                version=quotation.version + 1,
                subtotal=subtotal,
                discount=cleaned_discount,
                tax=cleaned_tax,
                total=total,
                terms=terms if terms is not None else quotation.terms,
                payment_schedule=payment_schedule if payment_schedule is not None else quotation.payment_schedule,
                valid_until=valid_until if valid_until is not None else quotation.valid_until,
                status=QuotationStatus.DRAFT,
                notes=notes if notes is not None else quotation.notes,
            )

            for item_row in item_rows:
                item_row.quotation = new_version
            QuotationItemRepository.bulk_create(item_rows)

            AuditLogService.record(
                action=AuditAction.CREATE,
                entity_type="quotation",
                entity_id=new_version.id,
                company_id=new_version.company_id,
                actor_user=actor_user,
                after_state=_quotation_audit_state(new_version),
                request=request,
            )

            return new_version

    @classmethod
    def _transition_status(
        cls,
        quotation: Quotation,
        from_status: str,
        to_status: str,
        action: AuditAction,
        conflict_message: str,
        actor_user: Any = None,
        request: Any = None,
    ) -> Quotation:
        """
        Shared machinery for send/approve/reject (BE-041): every one of
        them is a single fixed source-status -> target-status transition
        on the latest version, audited under entity_type "quotation" (a
        status change is recorded on the same row, not a separate entity
        -- matches ProjectService.transition_status's own convention).
        """
        with transaction.atomic():
            _ensure_latest_version(quotation)

            if quotation.status != from_status:
                raise ConflictError(conflict_message)

            before_state = _quotation_audit_state(quotation)
            quotation = QuotationRepository.save(quotation, {"status": to_status})

            AuditLogService.record(
                action=action,
                entity_type="quotation",
                entity_id=quotation.id,
                company_id=quotation.company_id,
                actor_user=actor_user,
                before_state=before_state,
                after_state=_quotation_audit_state(quotation),
                request=request,
            )

            return quotation

    @classmethod
    def send_quotation(cls, quotation: Quotation, actor_user: Any = None, request: Any = None) -> Quotation:
        """
        `draft -> sent` (BE-041). No dedicated `internal_review` transition
        exists (Backend Lead decision, Sprint 5 planning) -- this is the
        only forward transition out of `draft`.
        """
        return cls._transition_status(
            quotation,
            from_status=QuotationStatus.DRAFT,
            to_status=QuotationStatus.SENT,
            action=AuditAction.UPDATE,
            conflict_message="Only a draft quotation can be sent.",
            actor_user=actor_user,
            request=request,
        )

    @classmethod
    def approve_quotation(cls, quotation: Quotation, actor_user: Any = None, request: Any = None) -> Quotation:
        """
        `sent -> approved` (BE-041). Uses AuditAction.APPROVE -- the enum
        value Database_Schema.md's own audit_log.action set reserves for
        exactly this kind of event, unlike every other status change in
        this codebase (which are logged as plain UPDATE).
        """
        return cls._transition_status(
            quotation,
            from_status=QuotationStatus.SENT,
            to_status=QuotationStatus.APPROVED,
            action=AuditAction.APPROVE,
            conflict_message="Only a sent quotation can be approved.",
            actor_user=actor_user,
            request=request,
        )

    @classmethod
    def reject_quotation(cls, quotation: Quotation, actor_user: Any = None, request: Any = None) -> Quotation:
        """
        `sent -> rejected` (BE-041). Always the terminal `rejected` status
        -- Backend Lead decision, Sprint 5 planning: `revision_requested`
        is never set by this endpoint; a client asking for changes instead
        is handled by staff calling `/revise` directly on this quotation
        (revise has no status precondition of its own, so it works from
        `rejected` too).
        """
        return cls._transition_status(
            quotation,
            from_status=QuotationStatus.SENT,
            to_status=QuotationStatus.REJECTED,
            action=AuditAction.UPDATE,
            conflict_message="Only a sent quotation can be rejected.",
            actor_user=actor_user,
            request=request,
        )
