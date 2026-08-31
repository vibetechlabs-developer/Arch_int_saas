import uuid
from decimal import ROUND_HALF_UP, Decimal
from typing import Any, Dict, Optional
from django.db import transaction
from django.db.models import QuerySet
from rest_framework import exceptions as drf_exceptions

from apps.audit.models import AuditAction
from apps.audit.services import AuditLogService
from apps.boq import selectors, validators
from apps.boq.models import BOQ, BOQItem, BOQSection
from apps.boq.repositories import BOQItemRepository, BOQRepository, BOQSectionRepository
from apps.common.exceptions import ConflictError
from apps.products.services import ProductService
from apps.projects.models import Project

SECTION_AUDITED_FIELDS = ("name", "sort_order")
ITEM_AUDITED_FIELDS = (
    "product_id",
    "description",
    "quantity",
    "unit",
    "rate",
    "discount",
    "tax",
    "amount",
    "is_optional",
    "is_alternative",
    "notes",
)


def _section_audit_state(section: BOQSection) -> Dict[str, Any]:
    return {field: getattr(section, field) for field in SECTION_AUDITED_FIELDS}


def _serialize_item_audit_value(value: Any) -> Any:
    """
    Same JSONField-has-no-custom-encoder reasoning as Project (BE-029)
    and Product (BE-033): BOQItem's audited fields include a FK id
    (product_id, a uuid.UUID) and four Decimal fields.
    """
    if isinstance(value, uuid.UUID):
        return str(value)
    if isinstance(value, Decimal):
        return str(value)
    return value


def _item_audit_state(item: BOQItem) -> Dict[str, Any]:
    return {
        field: _serialize_item_audit_value(getattr(item, field)) for field in ITEM_AUDITED_FIELDS
    }


def _compute_amount(quantity: Decimal, rate: Decimal) -> Decimal:
    """
    quantity * rate, per BOQ_API.md's documented formula. Explicitly
    quantized to 2 decimal places (matching amount's own
    decimal_places=2) rather than left at the raw multiplication's
    precision (e.g. 2.00 * 10.00 == Decimal("20.0000")) -- the DB column
    would silently round it on the next fetch, but the in-memory value
    used for the immediate API response and audit log entry would stay
    unrounded until then. Caught by a real test failure, not assumed.
    """
    return (Decimal(quantity) * Decimal(rate)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


class BOQService:
    """
    Business logic and orchestration service for BOQ management (BE-035).
    BOQ has no create/update/delete endpoint of its own — it is an
    implicit 1:1 companion to Project, auto-created on first access
    (Backend Lead decision, 2026-08-31). Audit logging wired inline, not
    deferred — Sprint 4 has no separate "Audit Logs" task, mirroring
    Sprint 3's Product Catalog precedent (BE-031) rather than Project's
    BE-024-029 split.
    """

    @classmethod
    def get_or_create_boq_for_project(
        cls,
        project: Project,
        actor_user: Any = None,
        request: Any = None,
    ) -> BOQ:
        """
        Fetch the given Project's BOQ, creating one if it doesn't exist
        yet. Idempotent — a second call for the same project returns the
        existing row, never creates a duplicate (backed by `project`
        being a OneToOneField).
        """
        boq = BOQRepository.get_by_project(project)
        if boq is not None:
            return boq

        with transaction.atomic():
            boq = BOQRepository.create_for_project(project)

            AuditLogService.record(
                action=AuditAction.CREATE,
                entity_type="boq",
                entity_id=boq.id,
                company_id=project.company_id,
                actor_user=actor_user,
                after_state={"project_id": str(project.id)},
                request=request,
            )

            return boq


class BOQSectionService:
    """
    Business logic and orchestration service for BOQSection management
    (BE-035). Every method takes an already-authorized `boq` instance
    (tenant authorization for the parent Project/BOQ happens at the view
    layer, mirroring ProjectMemberService's pattern) — except
    get/update/delete-by-id, which resolve tenant scope through
    `section.boq.company_id` since BOQSection has no direct company
    column (Database_Schema.md's own schema, not an oversight).
    """

    @classmethod
    def list_sections(cls, boq: BOQ) -> QuerySet[BOQSection]:
        return BOQSectionRepository.all_for_boq(boq.id)

    @classmethod
    def create_section(
        cls,
        boq: BOQ,
        name: str,
        actor_user: Any = None,
        request: Any = None,
    ) -> BOQSection:
        """
        Create a new BOQSection, appended to the end of the BOQ's existing
        sections. `sort_order` is auto-assigned (max existing + 1) — not
        an input field, per BOQ_API.md's "Add a section" row listing no
        fields at all beyond implying a name.
        """
        with transaction.atomic():
            cleaned_name = validators.require_section_name(name)
            next_sort_order = BOQSectionRepository.max_sort_order_for_boq(boq.id) + 1

            section = BOQSectionRepository.create(
                boq=boq, name=cleaned_name, sort_order=next_sort_order
            )

            AuditLogService.record(
                action=AuditAction.CREATE,
                entity_type="boq_section",
                entity_id=section.id,
                company_id=boq.company_id,
                actor_user=actor_user,
                after_state=_section_audit_state(section),
                request=request,
            )

            return section

    @classmethod
    def get_section_by_id(
        cls,
        section_id: str | uuid.UUID,
        company_id: Optional[str | uuid.UUID] = None,
    ) -> BOQSection:
        """
        Retrieve an active, non-deleted BOQSection by primary key UUID.
        Raises NotFound if it does not exist, is soft-deleted, or its
        parent BOQ belongs to another company.
        """
        section = BOQSectionRepository.get_by_id(section_id)

        if company_id is not None and str(section.boq.company_id) != str(company_id):
            raise drf_exceptions.NotFound("The requested BOQ section was not found.")

        return section

    @classmethod
    def update_section(
        cls,
        section_id: str | uuid.UUID,
        validated_data: Dict[str, Any],
        company_id: Optional[str | uuid.UUID] = None,
        actor_user: Any = None,
        request: Any = None,
    ) -> BOQSection:
        """
        Update an existing BOQSection's name. Added for consistency with
        every other module in this codebase (BOQ_API.md documents no
        PATCH for sections at all) — the same "add missing CRUD" Backend
        Lead decision BE-031 established for Category/Subcategory/Product
        DELETE.
        """
        with transaction.atomic():
            section = cls.get_section_by_id(section_id, company_id=company_id)
            before_state = _section_audit_state(section)

            fields: Dict[str, Any] = {}
            if "name" in validated_data:
                fields["name"] = validators.require_section_name(validated_data["name"])

            section = BOQSectionRepository.save(section, fields)

            AuditLogService.record(
                action=AuditAction.UPDATE,
                entity_type="boq_section",
                entity_id=section.id,
                company_id=section.boq.company_id,
                actor_user=actor_user,
                before_state=before_state,
                after_state=_section_audit_state(section),
                request=request,
            )

            return section

    @classmethod
    def soft_delete_section(
        cls,
        section_id: str | uuid.UUID,
        company_id: Optional[str | uuid.UUID] = None,
        actor_user: Any = None,
        request: Any = None,
    ) -> None:
        """
        Soft-delete a BOQSection. Resolves BE-035's documented deferral
        (mirrors BE-031/032's identical Category->Subcategory guard):
        blocked with a 409 ConflictError if the section has any active
        (non-deleted) Item.
        """
        with transaction.atomic():
            section = cls.get_section_by_id(section_id, company_id=company_id)

            if selectors.has_active_items_for_section(section.id):
                raise ConflictError(
                    "This section has one or more items and cannot be deleted."
                )

            section_id_val = section.id
            company_id_val = section.boq.company_id
            before_state = _section_audit_state(section)

            BOQSectionRepository.soft_delete(section)

            AuditLogService.record(
                action=AuditAction.DELETE,
                entity_type="boq_section",
                entity_id=section_id_val,
                company_id=company_id_val,
                actor_user=actor_user,
                before_state=before_state,
                request=request,
            )


class BOQItemService:
    """
    Business logic and orchestration service for BOQItem management
    (BE-036). `amount` is always server-computed (`quantity * rate`,
    BOQ_API.md's own documented formula, explicitly "never trusted from
    client") — no caller can set it directly. Every method takes an
    already-authorized `section` instance for create, mirroring
    BOQSectionService's own pattern — get/update/delete-by-id resolve
    tenant scope through `item.boq_section.boq.company_id`.
    """

    @classmethod
    def list_items(cls, section: BOQSection) -> QuerySet[BOQItem]:
        return BOQItemRepository.all_for_section(section.id)

    @classmethod
    def create_item(
        cls,
        section: BOQSection,
        product_id: Optional[str | uuid.UUID] = None,
        description: str = "",
        quantity: Any = None,
        unit: str = "",
        rate: Any = None,
        discount: Any = None,
        tax: Any = None,
        is_optional: bool = False,
        is_alternative: bool = False,
        notes: str = "",
        actor_user: Any = None,
        request: Any = None,
    ) -> BOQItem:
        """
        Create a new BOQItem under an already-authorized Section.

        A product reference is optional (BOQ_API.md: "product reference
        or free-text description"). When `product_id` is supplied:
        - tenant invariant enforced by reusing
          ProductService.get_product_by_id(product_id, company_id=...),
          which already raises NotFound on cross-tenant access — the same
          reuse-don't-duplicate pattern BE-025/BE-033 established for
          Project.client/Product.subcategory.
        - `description`/`unit`/`rate`/`tax` default from the product
          (name/unit/default_selling_rate/tax_rate) when not explicitly
          supplied, per BOQ_API.md's Notes ("inherit default cost/rate/
          unit/tax").
        Without a product, `description`/`unit`/`rate` have no sensible
        default and are required — raises ValidationError if missing.
        """
        with transaction.atomic():
            if quantity is None:
                raise drf_exceptions.ValidationError({"quantity": ["quantity is required."]})

            product = None
            if product_id:
                product = ProductService.get_product_by_id(
                    product_id, company_id=section.boq.company_id
                )

            cleaned_description = (description or "").strip()
            if not cleaned_description:
                if product is not None:
                    cleaned_description = product.name
                else:
                    raise drf_exceptions.ValidationError(
                        {"description": ["description is required when no product is referenced."]}
                    )

            cleaned_unit = unit or (product.unit if product is not None else "")
            if not cleaned_unit:
                raise drf_exceptions.ValidationError(
                    {"unit": ["unit is required when no product is referenced or the product has no default unit."]}
                )

            cleaned_rate = rate if rate is not None else (
                product.default_selling_rate if product is not None else None
            )
            if cleaned_rate is None:
                raise drf_exceptions.ValidationError(
                    {"rate": ["rate is required when no product is referenced or the product has no default selling rate."]}
                )

            if tax is not None:
                cleaned_tax = tax
            elif product is not None and product.tax_rate is not None:
                cleaned_tax = product.tax_rate
            else:
                cleaned_tax = 0

            cleaned_discount = discount if discount is not None else 0

            amount = _compute_amount(quantity, cleaned_rate)

            item = BOQItemRepository.create(
                boq_section=section,
                product=product,
                description=cleaned_description,
                quantity=quantity,
                unit=cleaned_unit,
                rate=cleaned_rate,
                discount=cleaned_discount,
                tax=cleaned_tax,
                amount=amount,
                is_optional=is_optional,
                is_alternative=is_alternative,
                notes=notes or "",
            )

            AuditLogService.record(
                action=AuditAction.CREATE,
                entity_type="boq_item",
                entity_id=item.id,
                company_id=section.boq.company_id,
                actor_user=actor_user,
                after_state=_item_audit_state(item),
                request=request,
            )

            return item

    @classmethod
    def get_item_by_id(
        cls,
        item_id: str | uuid.UUID,
        company_id: Optional[str | uuid.UUID] = None,
    ) -> BOQItem:
        """
        Retrieve an active, non-deleted BOQItem by primary key UUID.
        Raises NotFound if it does not exist, is soft-deleted, or its
        parent BOQ belongs to another company.
        """
        item = BOQItemRepository.get_by_id(item_id)

        if company_id is not None and str(item.boq_section.boq.company_id) != str(company_id):
            raise drf_exceptions.NotFound("The requested BOQ item was not found.")

        return item

    @classmethod
    def update_item(
        cls,
        item_id: str | uuid.UUID,
        validated_data: Dict[str, Any],
        company_id: Optional[str | uuid.UUID] = None,
        actor_user: Any = None,
        request: Any = None,
    ) -> BOQItem:
        """
        Update an existing BOQItem. Matches BOQ_API.md's documented PATCH
        fields exactly: "quantity/rate/discount/tax/notes/optional/
        alternative flags" — description/unit are also editable (BE-036's
        own extension, since a free-text item's description/unit are its
        only identifying content and excluding them from edit would make
        typos unfixable) but `product`/`boq_section` are not (reassignment
        not documented as supported, mirrors every prior module's
        exclusion of its own parent/identity reference from PATCH).
        `amount` is always recomputed from the resulting quantity/rate,
        never taken from the request.
        """
        with transaction.atomic():
            item = cls.get_item_by_id(item_id, company_id=company_id)
            before_state = _item_audit_state(item)

            fields: Dict[str, Any] = {}

            if "description" in validated_data:
                cleaned = (validated_data["description"] or "").strip()
                if not cleaned:
                    raise drf_exceptions.ValidationError(
                        {"description": ["description cannot be blank or empty."]}
                    )
                fields["description"] = cleaned

            if "unit" in validated_data:
                fields["unit"] = validated_data["unit"] or ""

            for field in ("discount", "tax", "notes"):
                if field in validated_data:
                    fields[field] = validated_data[field]

            for field in ("is_optional", "is_alternative"):
                if field in validated_data:
                    fields[field] = validated_data[field]

            quantity = validated_data.get("quantity", item.quantity)
            rate = validated_data.get("rate", item.rate)
            if "quantity" in validated_data:
                fields["quantity"] = quantity
            if "rate" in validated_data:
                fields["rate"] = rate
            fields["amount"] = _compute_amount(quantity, rate)

            item = BOQItemRepository.save(item, fields)

            AuditLogService.record(
                action=AuditAction.UPDATE,
                entity_type="boq_item",
                entity_id=item.id,
                company_id=item.boq_section.boq.company_id,
                actor_user=actor_user,
                before_state=before_state,
                after_state=_item_audit_state(item),
                request=request,
            )

            return item

    @classmethod
    def soft_delete_item(
        cls,
        item_id: str | uuid.UUID,
        company_id: Optional[str | uuid.UUID] = None,
        actor_user: Any = None,
        request: Any = None,
    ) -> None:
        """
        Soft-delete a BOQItem. No further delete guard needed -- nothing
        in this sprint's scope references a boq_item yet.
        """
        with transaction.atomic():
            item = cls.get_item_by_id(item_id, company_id=company_id)
            item_id_val = item.id
            company_id_val = item.boq_section.boq.company_id
            before_state = _item_audit_state(item)

            BOQItemRepository.soft_delete(item)

            AuditLogService.record(
                action=AuditAction.DELETE,
                entity_type="boq_item",
                entity_id=item_id_val,
                company_id=company_id_val,
                actor_user=actor_user,
                before_state=before_state,
                request=request,
            )
