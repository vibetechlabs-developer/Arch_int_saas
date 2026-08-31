import uuid
from typing import Any, Dict, Optional
from django.db import transaction
from django.db.models import QuerySet
from rest_framework import exceptions as drf_exceptions

from apps.audit.models import AuditAction
from apps.audit.services import AuditLogService
from apps.common.exceptions import ConflictError
from apps.products import selectors, validators
from apps.products.models import ProductCategory, ProductSubcategory
from apps.products.repositories import ProductCategoryRepository, ProductSubcategoryRepository

CATEGORY_AUDITED_FIELDS = ("name",)
SUBCATEGORY_AUDITED_FIELDS = ("name", "category_id")


def _category_audit_state(category: ProductCategory) -> Dict[str, Any]:
    return {field: getattr(category, field) for field in CATEGORY_AUDITED_FIELDS}


def _subcategory_audit_state(subcategory: ProductSubcategory) -> Dict[str, Any]:
    return {
        field: str(getattr(subcategory, field)) if field.endswith("_id") else getattr(subcategory, field)
        for field in SUBCATEGORY_AUDITED_FIELDS
    }


class ProductCategoryService:
    """
    Business logic and orchestration service for ProductCategory
    management (BE-031). Mirrors apps.clients.services.ClientService's
    structure (BACKEND_RULES.md: View -> Serializer -> Service ->
    Repository -> Model), including inline audit logging (Sprint 3 has no
    separate "audit logs" task the way Project's BE-024-029 split did, so
    this follows Client's BE-023 precedent of wiring AuditLogService
    directly into the CRUD task itself).
    """

    @classmethod
    def list_categories(
        cls,
        company_id: Optional[str | uuid.UUID] = None,
        ordering: str = "-created_at",
    ) -> QuerySet[ProductCategory]:
        return selectors.list_categories(company_id=company_id, ordering=ordering)

    @classmethod
    def list_categories_for_viewer(
        cls,
        is_platform_admin: bool,
        resolved_company_id: Optional[str | uuid.UUID],
        admin_company_id_param: Optional[str],
        ordering: str = "-created_at",
    ) -> QuerySet[ProductCategory]:
        """
        Mirrors ClientService.list_clients_for_viewer exactly.
        """
        target_company_id = admin_company_id_param if is_platform_admin else resolved_company_id
        return cls.list_categories(company_id=target_company_id, ordering=ordering)

    @classmethod
    def resolve_create_target_company_id(
        cls,
        is_platform_admin: bool,
        resolved_company_id: Optional[str | uuid.UUID],
        supplied_company_id: Optional[str | uuid.UUID],
    ) -> str | uuid.UUID:
        """
        Mirrors ClientService.resolve_create_target_company_id exactly — a
        client-supplied companyId is never trusted as the authorization
        boundary (Tenant.md §4).
        """
        if is_platform_admin:
            if not supplied_company_id:
                raise drf_exceptions.ValidationError(
                    {"companyId": ["companyId is required for platform admin category creation."]}
                )
            return supplied_company_id

        if supplied_company_id and str(supplied_company_id) != str(resolved_company_id):
            raise drf_exceptions.PermissionDenied(
                "You do not have permission to create categories for this company."
            )
        return resolved_company_id

    @classmethod
    def get_category_by_id(
        cls,
        category_id: str | uuid.UUID,
        company_id: Optional[str | uuid.UUID] = None,
    ) -> ProductCategory:
        """
        Retrieve an active, non-deleted ProductCategory by primary key
        UUID. Raises NotFound if it does not exist, is soft-deleted, or
        belongs to another company.
        """
        category = ProductCategoryRepository.get_by_id(category_id)

        if company_id is not None and str(category.company_id) != str(company_id):
            raise drf_exceptions.NotFound("The requested product category was not found.")

        return category

    @classmethod
    def create_category(
        cls,
        company_id: str | uuid.UUID,
        name: str,
        actor_user: Any = None,
        request: Any = None,
    ) -> ProductCategory:
        """
        Create a new ProductCategory within a Company tenant.
        """
        with transaction.atomic():
            company = ProductCategoryRepository.get_company_by_id(company_id)
            cleaned_name = validators.require_category_name(name)

            category = ProductCategoryRepository.create(company=company, name=cleaned_name)

            AuditLogService.record(
                action=AuditAction.CREATE,
                entity_type="product_category",
                entity_id=category.id,
                company_id=company.id,
                actor_user=actor_user,
                after_state=_category_audit_state(category),
                request=request,
            )

            return category

    @classmethod
    def update_category(
        cls,
        category_id: str | uuid.UUID,
        validated_data: Dict[str, Any],
        company_id: Optional[str | uuid.UUID] = None,
        actor_user: Any = None,
        request: Any = None,
    ) -> ProductCategory:
        """
        Update an existing ProductCategory's name.
        """
        with transaction.atomic():
            category = cls.get_category_by_id(category_id, company_id=company_id)
            before_state = _category_audit_state(category)

            fields: Dict[str, Any] = {}
            if "name" in validated_data:
                fields["name"] = validators.require_category_name(validated_data["name"])

            category = ProductCategoryRepository.save(category, fields)

            AuditLogService.record(
                action=AuditAction.UPDATE,
                entity_type="product_category",
                entity_id=category.id,
                company_id=category.company_id,
                actor_user=actor_user,
                before_state=before_state,
                after_state=_category_audit_state(category),
                request=request,
            )

            return category

    @classmethod
    def soft_delete_category(
        cls,
        category_id: str | uuid.UUID,
        company_id: Optional[str | uuid.UUID] = None,
        actor_user: Any = None,
        request: Any = None,
    ) -> None:
        """
        Soft-delete a ProductCategory by setting deleted_at timestamp.

        Resolves BE-031's documented deferral (mirrors BE-024's identical
        resolution for Client -> Project): blocked with a 409 ConflictError
        if the category has any active (non-deleted) Subcategory —
        Backend Lead decision, 2026-08-31, mirroring the Client-cannot-
        delete-while-active-Projects-exist guard exactly.
        """
        with transaction.atomic():
            category = cls.get_category_by_id(category_id, company_id=company_id)

            if selectors.has_active_subcategories_for_category(category.id):
                raise ConflictError(
                    "This category has one or more subcategories and cannot be deleted."
                )

            category_id_val = category.id
            company_id_val = category.company_id
            before_state = _category_audit_state(category)

            ProductCategoryRepository.soft_delete(category)

            AuditLogService.record(
                action=AuditAction.DELETE,
                entity_type="product_category",
                entity_id=category_id_val,
                company_id=company_id_val,
                actor_user=actor_user,
                before_state=before_state,
                request=request,
            )


class ProductSubcategoryService:
    """
    Business logic and orchestration service for ProductSubcategory
    management (BE-032). List/create take an already-authorized `category`
    instance (tenant authorization for the parent happens at the view
    layer, mirroring ProjectMemberService's pattern) — get/update/delete
    take a bare subcategory_id + optional company_id, mirroring every
    other flat-detail-endpoint service in this codebase.
    """

    @classmethod
    def list_subcategories_for_category(
        cls,
        category: ProductCategory,
        ordering: str = "-created_at",
    ) -> QuerySet[ProductSubcategory]:
        return selectors.list_subcategories_for_category(category.id, ordering=ordering)

    @classmethod
    def create_subcategory(
        cls,
        category: ProductCategory,
        name: str,
        actor_user: Any = None,
        request: Any = None,
    ) -> ProductSubcategory:
        """
        Create a new ProductSubcategory under an already-authorized
        Category. `company` is copied from the parent category, never
        supplied independently — a subcategory's tenant is always its
        category's tenant.
        """
        with transaction.atomic():
            cleaned_name = validators.require_subcategory_name(name)

            subcategory = ProductSubcategoryRepository.create(
                company=category.company, category=category, name=cleaned_name
            )

            AuditLogService.record(
                action=AuditAction.CREATE,
                entity_type="product_subcategory",
                entity_id=subcategory.id,
                company_id=category.company_id,
                actor_user=actor_user,
                after_state=_subcategory_audit_state(subcategory),
                request=request,
            )

            return subcategory

    @classmethod
    def get_subcategory_by_id(
        cls,
        subcategory_id: str | uuid.UUID,
        company_id: Optional[str | uuid.UUID] = None,
    ) -> ProductSubcategory:
        """
        Retrieve an active, non-deleted ProductSubcategory by primary key
        UUID. Raises NotFound if it does not exist, is soft-deleted, or
        belongs to another company.
        """
        subcategory = ProductSubcategoryRepository.get_by_id(subcategory_id)

        if company_id is not None and str(subcategory.company_id) != str(company_id):
            raise drf_exceptions.NotFound("The requested product subcategory was not found.")

        return subcategory

    @classmethod
    def update_subcategory(
        cls,
        subcategory_id: str | uuid.UUID,
        validated_data: Dict[str, Any],
        company_id: Optional[str | uuid.UUID] = None,
        actor_user: Any = None,
        request: Any = None,
    ) -> ProductSubcategory:
        """
        Update an existing ProductSubcategory's name. `category` is not
        editable here — not documented as a supported reassignment
        anywhere (BOQ_API.md's PATCH row is for Product, not Subcategory,
        and this endpoint's own PATCH wasn't documented at all — see
        BE-031's "add DELETE anyway" decision, which applies the same
        reasoning to PATCH/PUT here).
        """
        with transaction.atomic():
            subcategory = cls.get_subcategory_by_id(subcategory_id, company_id=company_id)
            before_state = _subcategory_audit_state(subcategory)

            fields: Dict[str, Any] = {}
            if "name" in validated_data:
                fields["name"] = validators.require_subcategory_name(validated_data["name"])

            subcategory = ProductSubcategoryRepository.save(subcategory, fields)

            AuditLogService.record(
                action=AuditAction.UPDATE,
                entity_type="product_subcategory",
                entity_id=subcategory.id,
                company_id=subcategory.company_id,
                actor_user=actor_user,
                before_state=before_state,
                after_state=_subcategory_audit_state(subcategory),
                request=request,
            )

            return subcategory

    @classmethod
    def soft_delete_subcategory(
        cls,
        subcategory_id: str | uuid.UUID,
        company_id: Optional[str | uuid.UUID] = None,
        actor_user: Any = None,
        request: Any = None,
    ) -> None:
        """
        Soft-delete a ProductSubcategory by setting deleted_at timestamp.

        Deferred (documented, not a gap, mirrors BE-031's identical
        deferral for Category): the "block delete if active Products
        exist" guard can't be built until BE-033 (Product) exists. BE-033
        adds it, the same way BE-032 (this task) added Category's guard.
        """
        with transaction.atomic():
            subcategory = cls.get_subcategory_by_id(subcategory_id, company_id=company_id)
            subcategory_id_val = subcategory.id
            company_id_val = subcategory.company_id
            before_state = _subcategory_audit_state(subcategory)

            ProductSubcategoryRepository.soft_delete(subcategory)

            AuditLogService.record(
                action=AuditAction.DELETE,
                entity_type="product_subcategory",
                entity_id=subcategory_id_val,
                company_id=company_id_val,
                actor_user=actor_user,
                before_state=before_state,
                request=request,
            )
