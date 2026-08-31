import uuid
from typing import Any, Dict, Optional
from django.db import transaction
from django.db.models import QuerySet
from rest_framework import exceptions as drf_exceptions

from apps.audit.models import AuditAction
from apps.audit.services import AuditLogService
from apps.products import selectors, validators
from apps.products.models import ProductCategory
from apps.products.repositories import ProductCategoryRepository

CATEGORY_AUDITED_FIELDS = ("name",)


def _category_audit_state(category: ProductCategory) -> Dict[str, Any]:
    return {field: getattr(category, field) for field in CATEGORY_AUDITED_FIELDS}


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

        Deferred (documented, not a gap, mirrors BE-022/023's identical
        deferral for Client): the "block delete if active Subcategories
        exist" guard can't be built until BE-032 (ProductSubcategory)
        exists. BE-032 adds it, the same way BE-024 added Client's guard
        once Project existed.
        """
        with transaction.atomic():
            category = cls.get_category_by_id(category_id, company_id=company_id)
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
