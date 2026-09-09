import datetime
import uuid
from decimal import ROUND_HALF_UP, Decimal
from typing import Any, Dict, List, Optional

from django.db import transaction
from django.db.models import QuerySet
from django.utils import timezone
from rest_framework import exceptions as drf_exceptions

from apps.audit.models import AuditAction
from apps.audit.services import AuditLogService
from apps.common.exceptions import ConflictError
from apps.invoices import selectors, validators
from apps.invoices.models import Invoice, InvoiceItem, InvoiceStatus
from apps.invoices.repositories import InvoiceItemRepository, InvoiceRepository
from apps.payments.repositories import PaymentRepository
from apps.projects.models import Project
from apps.quotations.models import QuotationStatus
from apps.quotations.services import QuotationService

INVOICE_AUDITED_FIELDS = (
    "project_id",
    "quotation_id",
    "client_id",
    "invoice_number",
    "subtotal",
    "discount",
    "tax",
    "total",
    "due_date",
    "payment_terms",
    "status",
    "notes",
)

# Statuses from which an invoice may still be cancelled -- PAID and
# CANCELLED itself are terminal (Backend Lead decision, Sprint 6 planning;
# Finance_API.md documents the /cancel action but not its source-status
# preconditions).
CANCELLABLE_STATUSES = (InvoiceStatus.DRAFT, InvoiceStatus.SENT, InvoiceStatus.PARTIALLY_PAID)


def _serialize_invoice_audit_value(value: Any) -> Any:
    """
    Same JSONField-has-no-custom-encoder reasoning as
    apps.quotations.services._serialize_quotation_audit_value.
    """
    if isinstance(value, (datetime.date, datetime.datetime)):
        return value.isoformat()
    if isinstance(value, uuid.UUID):
        return str(value)
    if isinstance(value, Decimal):
        return str(value)
    return value


def _invoice_audit_state(invoice: Invoice) -> Dict[str, Any]:
    return {
        field: _serialize_invoice_audit_value(getattr(invoice, field))
        for field in INVOICE_AUDITED_FIELDS
    }


def _compute_amount(quantity: Decimal, rate: Decimal) -> Decimal:
    """
    quantity * rate, quantized to 2 decimal places -- duplicated from
    apps.quotations.services._compute_amount/apps.boq.services._compute_amount
    for the same "the formula is the entire function, a cross-app import
    buys no reuse" reasoning already established twice.
    """
    return (Decimal(quantity) * Decimal(rate)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _build_items_from_input(items_data: List[Dict[str, Any]]):
    """
    Build InvoiceItem rows from caller-supplied item data. Unlike
    QuotationItem/BOQItem, InvoiceItem has no `product` FK
    (Database_Schema.md's literal `invoice_item` column list has none) --
    every item is a plain description/quantity/unit/rate entry, no
    product-defaulting logic needed.
    """
    item_rows: List[InvoiceItem] = []
    subtotal = Decimal("0.00")

    for raw in items_data:
        description = (raw.get("description") or "").strip()
        if not description:
            raise drf_exceptions.ValidationError({"items": ["description is required."]})

        rate = raw.get("rate")
        if rate is None:
            raise drf_exceptions.ValidationError({"items": ["rate is required."]})

        quantity = validators.require_positive_quantity(raw.get("quantity"))
        amount = _compute_amount(quantity, rate)
        subtotal += amount

        item_rows.append(
            InvoiceItem(
                description=description,
                quantity=quantity,
                unit=raw.get("unit") or "",
                rate=rate,
                amount=amount,
            )
        )

    return item_rows, subtotal


class InvoiceService:
    """
    Business logic and orchestration service for Invoice management
    (BE-042). An Invoice is created either from an approved Quotation
    (copies its items and subtotal/discount/tax/total verbatim, the same
    reuse pattern QuotationService.create_quotation established for
    copying a BOQ's summary) or ad hoc (caller-supplied items, flat
    discount/tax amounts). `client` is always derived from
    `project.client_id`, never caller-supplied.
    """

    @classmethod
    def list_invoices_for_project(cls, project: Project, ordering: str = "-created_at") -> QuerySet[Invoice]:
        return selectors.list_invoices_for_project(project.id, ordering=ordering)

    @classmethod
    def get_invoice_by_id(
        cls,
        invoice_id: str | uuid.UUID,
        company_id: Optional[str | uuid.UUID] = None,
    ) -> Invoice:
        """
        Retrieve an active, non-deleted Invoice by primary key UUID.
        Raises NotFound if it does not exist, is soft-deleted, or belongs
        to another company.
        """
        invoice = InvoiceRepository.get_by_id(invoice_id)

        if company_id is not None and str(invoice.company_id) != str(company_id):
            raise drf_exceptions.NotFound("The requested invoice was not found.")

        return invoice

    @classmethod
    def compute_effective_status(cls, invoice: Invoice) -> str:
        """
        Read-time-only "overdue" derivation (Backend Lead decision,
        AskUserQuestion, Sprint 6 planning) -- `invoice.status` itself
        never stores `overdue`; this returns what the API should actually
        display: `overdue` whenever the persisted status is `sent` or
        `partially_paid` and `due_date` has passed, otherwise the
        persisted status unchanged. No cron/Celery Beat sweep needed --
        always accurate on every read.
        """
        if (
            invoice.status in (InvoiceStatus.SENT, InvoiceStatus.PARTIALLY_PAID)
            and invoice.due_date is not None
            and invoice.due_date < timezone.localdate()
        ):
            return InvoiceStatus.OVERDUE
        return invoice.status

    @classmethod
    def get_paid_amount(cls, invoice: Invoice) -> Decimal:
        """
        BE-074: the authoritative, backend-computed sum of this invoice's
        active (non-voided) payments. `InvoiceRepository.get_by_id`/
        `all_for_project` and `selectors.list_invoices_for_project` all
        annotate every Invoice they return with `paid_amount` (one query
        total, never N+1 -- see `apps.invoices.repositories.
        with_paid_amount`), so the common case here is reading that
        already-fetched value with zero extra queries. The one-time,
        single-row fallback query only fires for an Invoice instance that
        was mutated and returned in-memory without being re-fetched
        (create/update/send/cancel's own response) -- correct either way,
        never a missing or stale figure.
        """
        annotated = getattr(invoice, "paid_amount", None)
        if annotated is not None:
            return annotated
        return PaymentRepository.sum_active_amount_for_invoice(invoice.id)

    @classmethod
    def compute_outstanding_amount(cls, invoice: Invoice) -> Decimal:
        """
        BE-074: `max(total - paidAmount, 0)` -- overpayment (explicitly
        allowed, unchanged by this task: PaymentService.create_payment has
        no upper bound on amount, and recompute_status_from_payments
        already treats `paid_total >= total` as simply `paid`, nothing
        more) never produces a negative "balance due", which would read as
        the company owing the client money -- not a real state this
        product models. The real, larger paid figure is still reported by
        `paidAmount` unchanged; only the derived remaining-balance figure
        is floored at zero.
        """
        paid_amount = cls.get_paid_amount(invoice)
        remaining = invoice.total - paid_amount
        return remaining if remaining > 0 else Decimal("0.00")

    @classmethod
    def create_invoice(
        cls,
        project: Project,
        quotation_id: Optional[str | uuid.UUID] = None,
        items: Optional[List[Dict[str, Any]]] = None,
        discount: Any = None,
        tax: Any = None,
        due_date: Any = None,
        payment_terms: str = "",
        notes: str = "",
        actor_user: Any = None,
        request: Any = None,
    ) -> Invoice:
        """
        Create a new Invoice for an already-authorized Project.

        - `quotationId` supplied: the quotation must belong to the same
          company (reuses QuotationService.get_quotation_by_id, which
          already raises NotFound on cross-tenant access) and must be
          `approved` (Finance_API.md: "from...approved quotation") --
          raises ValidationError otherwise. Its items and subtotal/
          discount/tax/total are copied verbatim; `items` must not also be
          supplied (ambiguous intent).
        - `items` supplied instead (ad hoc): built manually, discount/tax
          are flat currency amounts from the request (default 0).
        - Neither supplied: invalid -- an invoice needs one source or the
          other (unlike Quotation, Invoice has no implicit BOQ fallback).
        """
        with transaction.atomic():
            if quotation_id and items is not None:
                raise drf_exceptions.ValidationError(
                    {"items": ["items cannot be supplied together with quotationId."]}
                )
            if not quotation_id and items is None:
                raise drf_exceptions.ValidationError(
                    {"items": ["Either quotationId or items must be supplied."]}
                )

            company = InvoiceRepository.get_company_by_id(project.company_id)

            if quotation_id:
                quotation = QuotationService.get_quotation_by_id(quotation_id, company_id=project.company_id)
                if quotation.status != QuotationStatus.APPROVED:
                    raise drf_exceptions.ValidationError(
                        {"quotationId": ["Only an approved quotation can be invoiced."]}
                    )

                item_rows = [
                    InvoiceItem(
                        description=quotation_item.description,
                        quantity=quotation_item.quantity,
                        unit=quotation_item.unit,
                        rate=quotation_item.rate,
                        amount=_compute_amount(quotation_item.quantity, quotation_item.rate),
                    )
                    for quotation_item in quotation.items.all()
                ]
                subtotal = quotation.subtotal
                cleaned_discount = quotation.discount
                cleaned_tax = quotation.tax
                total = quotation.total
            else:
                quotation = None
                item_rows, subtotal = _build_items_from_input(items)
                cleaned_discount = discount if discount is not None else Decimal("0.00")
                cleaned_tax = tax if tax is not None else Decimal("0.00")
                total = subtotal - cleaned_discount + cleaned_tax

            invoice_number = InvoiceRepository.next_invoice_number(project.company_id)

            invoice = InvoiceRepository.create(
                company=company,
                project=project,
                quotation=quotation,
                client=project.client,
                invoice_number=invoice_number,
                subtotal=subtotal,
                discount=cleaned_discount,
                tax=cleaned_tax,
                total=total,
                due_date=due_date,
                payment_terms=payment_terms or "",
                status=InvoiceStatus.DRAFT,
                notes=notes or "",
            )

            for item_row in item_rows:
                item_row.invoice = invoice
            InvoiceItemRepository.bulk_create(item_rows)

            AuditLogService.record(
                action=AuditAction.CREATE,
                entity_type="invoice",
                entity_id=invoice.id,
                company_id=company.id,
                actor_user=actor_user,
                after_state=_invoice_audit_state(invoice),
                request=request,
            )

            return invoice

    @classmethod
    def update_invoice(
        cls,
        invoice: Invoice,
        items: Optional[List[Dict[str, Any]]] = None,
        discount: Any = None,
        tax: Any = None,
        due_date: Any = None,
        payment_terms: Optional[str] = None,
        notes: Optional[str] = None,
        actor_user: Any = None,
        request: Any = None,
    ) -> Invoice:
        """
        Edit an already-authorized Invoice (BE-042) -- "draft only"
        (Finance_API.md), raises ConflictError (409) otherwise. `items`
        omitted keeps the existing items and subtotal unchanged; an
        explicit list replaces them entirely (hard-deletes the old rows --
        safe here, since a draft invoice has no payment/audit history of
        its own items to preserve) and recomputes `subtotal`. `discount`/
        `tax` carry over unless explicitly given either way; `total` is
        always recomputed from the invoice's own final subtotal/discount/
        tax.
        """
        with transaction.atomic():
            if invoice.status != InvoiceStatus.DRAFT:
                raise ConflictError("Only a draft invoice can be edited.")

            before_state = _invoice_audit_state(invoice)

            if items is not None:
                InvoiceItemRepository.delete_all_for_invoice(invoice.id)
                item_rows, subtotal = _build_items_from_input(items)
                for item_row in item_rows:
                    item_row.invoice = invoice
                InvoiceItemRepository.bulk_create(item_rows)
            else:
                subtotal = invoice.subtotal

            cleaned_discount = discount if discount is not None else invoice.discount
            cleaned_tax = tax if tax is not None else invoice.tax
            total = subtotal - cleaned_discount + cleaned_tax

            fields: Dict[str, Any] = {
                "subtotal": subtotal,
                "discount": cleaned_discount,
                "tax": cleaned_tax,
                "total": total,
            }
            if due_date is not None:
                fields["due_date"] = due_date
            if payment_terms is not None:
                fields["payment_terms"] = payment_terms
            if notes is not None:
                fields["notes"] = notes

            invoice = InvoiceRepository.save(invoice, fields)

            AuditLogService.record(
                action=AuditAction.UPDATE,
                entity_type="invoice",
                entity_id=invoice.id,
                company_id=invoice.company_id,
                actor_user=actor_user,
                before_state=before_state,
                after_state=_invoice_audit_state(invoice),
                request=request,
            )

            return invoice

    @classmethod
    def send_invoice(cls, invoice: Invoice, actor_user: Any = None, request: Any = None) -> Invoice:
        """`draft -> sent` (BE-042)."""
        with transaction.atomic():
            if invoice.status != InvoiceStatus.DRAFT:
                raise ConflictError("Only a draft invoice can be sent.")

            before_state = _invoice_audit_state(invoice)
            invoice = InvoiceRepository.save(invoice, {"status": InvoiceStatus.SENT})

            AuditLogService.record(
                action=AuditAction.UPDATE,
                entity_type="invoice",
                entity_id=invoice.id,
                company_id=invoice.company_id,
                actor_user=actor_user,
                before_state=before_state,
                after_state=_invoice_audit_state(invoice),
                request=request,
            )

            return invoice

    @classmethod
    def cancel_invoice(cls, invoice: Invoice, actor_user: Any = None, request: Any = None) -> Invoice:
        """
        Cancel an Invoice (BE-042). Allowed from draft/sent/
        partially_paid; blocked (409) once fully paid or already
        cancelled -- see CANCELLABLE_STATUSES.
        """
        with transaction.atomic():
            if invoice.status not in CANCELLABLE_STATUSES:
                raise ConflictError("This invoice cannot be cancelled from its current status.")

            before_state = _invoice_audit_state(invoice)
            invoice = InvoiceRepository.save(invoice, {"status": InvoiceStatus.CANCELLED})

            AuditLogService.record(
                action=AuditAction.UPDATE,
                entity_type="invoice",
                entity_id=invoice.id,
                company_id=invoice.company_id,
                actor_user=actor_user,
                before_state=before_state,
                after_state=_invoice_audit_state(invoice),
                request=request,
            )

            return invoice

    @classmethod
    def recompute_status_from_payments(
        cls,
        invoice: Invoice,
        paid_total: Decimal,
        actor_user: Any = None,
        request: Any = None,
    ) -> Invoice:
        """
        Called by PaymentService after recording or voiding a payment
        (BE-043). A cancelled invoice's status is never resurrected by
        payment math. Otherwise: fully covered -> paid; partially covered
        -> partially_paid; nothing covered (e.g. the only payment was
        voided) -> sent, the state a payable invoice reverts to (payments
        are only ever accepted against a non-draft, non-cancelled
        invoice -- see PaymentService.create_payment's own guard).
        """
        if invoice.status == InvoiceStatus.CANCELLED:
            return invoice

        if paid_total >= invoice.total and invoice.total > 0:
            new_status = InvoiceStatus.PAID
        elif paid_total > 0:
            new_status = InvoiceStatus.PARTIALLY_PAID
        else:
            new_status = InvoiceStatus.SENT

        if new_status == invoice.status:
            return invoice

        with transaction.atomic():
            before_state = _invoice_audit_state(invoice)
            invoice = InvoiceRepository.save(invoice, {"status": new_status})

            AuditLogService.record(
                action=AuditAction.UPDATE,
                entity_type="invoice",
                entity_id=invoice.id,
                company_id=invoice.company_id,
                actor_user=actor_user,
                before_state=before_state,
                after_state=_invoice_audit_state(invoice),
                request=request,
            )

            return invoice
