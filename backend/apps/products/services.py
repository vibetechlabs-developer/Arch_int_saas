import uuid
from decimal import Decimal
from typing import Any, Dict, Optional
from django.db import transaction
from django.db.models import QuerySet
from rest_framework import exceptions as drf_exceptions

from apps.audit.models import AuditAction
from apps.audit.services import AuditLogService
from apps.common import storage as storage_service
from apps.common.exceptions import ConflictError
from apps.products import selectors, validators
from apps.products.models import Product, ProductCategory, ProductStatus, ProductSubcategory
from apps.products.repositories import (
    ProductCategoryRepository,
    ProductRepository,
    ProductSubcategoryRepository,
)

CATEGORY_AUDITED_FIELDS = ("name",)
SUBCATEGORY_AUDITED_FIELDS = ("name", "category_id")
PRODUCT_AUDITED_FIELDS = (
    "name",
    "subcategory_id",
    "image_url",
    "unit",
    "default_cost",
    "default_selling_rate",
    "tax_rate",
    "status",
)


def _category_audit_state(category: ProductCategory) -> Dict[str, Any]:
    return {field: getattr(category, field) for field in CATEGORY_AUDITED_FIELDS}


def _subcategory_audit_state(subcategory: ProductSubcategory) -> Dict[str, Any]:
    return {
        field: str(getattr(subcategory, field)) if field.endswith("_id") else getattr(subcategory, field)
        for field in SUBCATEGORY_AUDITED_FIELDS
    }


def _serialize_product_audit_value(value: Any) -> Any:
    """
    apps.audit.models.AuditLog.before_state/after_state is a plain
    JSONField with no custom encoder (the same gap BE-029 found for
    Project) — Product's audited fields include a FK id (subcategory_id,
    a uuid.UUID) and three Decimal money/percentage fields, none of which
    json.JSONEncoder can serialize directly.
    """
    if isinstance(value, uuid.UUID):
        return str(value)
    if isinstance(value, Decimal):
        return str(value)
    return value


def _product_audit_state(product: Product) -> Dict[str, Any]:
    return {
        field: _serialize_product_audit_value(getattr(product, field))
        for field in PRODUCT_AUDITED_FIELDS
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

        Resolves BE-032's documented deferral (mirrors BE-031's identical
        resolution for Category): blocked with a 409 ConflictError if the
        subcategory has any active (non-deleted) Product.
        """
        with transaction.atomic():
            subcategory = cls.get_subcategory_by_id(subcategory_id, company_id=company_id)

            if selectors.has_active_products_for_subcategory(subcategory.id):
                raise ConflictError(
                    "This subcategory has one or more products and cannot be deleted."
                )

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


class ProductService:
    """
    Business logic and orchestration service for Product management
    (BE-033/034). Mirrors ProjectService's structure (BE-025) for the
    subcategory-tenant-invariant pattern: create_product reuses
    ProductSubcategoryService.get_subcategory_by_id(subcategory_id,
    company_id=...), which already raises NotFound on cross-tenant access,
    rather than duplicating that check. No search param on list — not
    documented; category/subcategory/status filters (BE-034) mirror the
    CRUD/Filters split BE-025/BE-028 established for Project.
    """

    @classmethod
    def list_products(
        cls,
        company_id: Optional[str | uuid.UUID] = None,
        category_id: Optional[str | uuid.UUID] = None,
        subcategory_id: Optional[str | uuid.UUID] = None,
        status: Optional[str] = None,
        ordering: str = "-created_at",
    ) -> QuerySet[Product]:
        return selectors.list_products(
            company_id=company_id,
            category_id=category_id,
            subcategory_id=subcategory_id,
            status=status,
            ordering=ordering,
        )

    @classmethod
    def list_products_for_viewer(
        cls,
        is_platform_admin: bool,
        resolved_company_id: Optional[str | uuid.UUID],
        admin_company_id_param: Optional[str],
        category_id: Optional[str | uuid.UUID] = None,
        subcategory_id: Optional[str | uuid.UUID] = None,
        status: Optional[str] = None,
        ordering: str = "-created_at",
    ) -> QuerySet[Product]:
        target_company_id = admin_company_id_param if is_platform_admin else resolved_company_id
        return cls.list_products(
            company_id=target_company_id,
            category_id=category_id,
            subcategory_id=subcategory_id,
            status=status,
            ordering=ordering,
        )

    @classmethod
    def resolve_create_target_company_id(
        cls,
        is_platform_admin: bool,
        resolved_company_id: Optional[str | uuid.UUID],
        supplied_company_id: Optional[str | uuid.UUID],
    ) -> str | uuid.UUID:
        """
        Mirrors ClientService/ProjectService's identical method exactly.
        """
        if is_platform_admin:
            if not supplied_company_id:
                raise drf_exceptions.ValidationError(
                    {"companyId": ["companyId is required for platform admin product creation."]}
                )
            return supplied_company_id

        if supplied_company_id and str(supplied_company_id) != str(resolved_company_id):
            raise drf_exceptions.PermissionDenied(
                "You do not have permission to create products for this company."
            )
        return resolved_company_id

    @classmethod
    def get_product_by_id(
        cls,
        product_id: str | uuid.UUID,
        company_id: Optional[str | uuid.UUID] = None,
    ) -> Product:
        """
        Retrieve an active, non-deleted Product by primary key UUID.
        Raises NotFound if it does not exist, is soft-deleted, or belongs
        to another company.
        """
        product = ProductRepository.get_by_id(product_id)

        if company_id is not None and str(product.company_id) != str(company_id):
            raise drf_exceptions.NotFound("The requested product was not found.")

        return product

    @classmethod
    def create_product(
        cls,
        company_id: str | uuid.UUID,
        subcategory_id: str | uuid.UUID,
        name: str,
        image_url: str = "",
        image_storage_key: str = "",
        unit: str = "",
        default_cost: Any = None,
        default_selling_rate: Any = None,
        tax_rate: Any = None,
        status: Optional[str] = None,
        actor_user: Any = None,
        request: Any = None,
    ) -> Product:
        """
        Create a new Product within a Company tenant.

        Tenant invariant enforcement: the subcategory must belong to the
        same company — enforced by reusing
        ProductSubcategoryService.get_subcategory_by_id(subcategory_id,
        company_id=...), the same pattern BE-025 established for
        Project.client. `status` is settable at create -- unlike Project,
        BOQ_API.md's own text explicitly lists "status" among Product's
        create fields ("Create product/work item (unit, default cost,
        default rate, tax, status)").
        """
        with transaction.atomic():
            company = ProductRepository.get_company_by_id(company_id)
            cleaned_name = validators.require_product_name(name)

            # Raises NotFound if subcategory doesn't exist or belongs to another company.
            subcategory = ProductSubcategoryService.get_subcategory_by_id(
                subcategory_id, company_id=company_id
            )

            product = ProductRepository.create(
                company=company,
                subcategory=subcategory,
                name=cleaned_name,
                image_url=image_url or "",
                image_storage_key=image_storage_key or "",
                unit=unit or "",
                default_cost=default_cost,
                default_selling_rate=default_selling_rate,
                tax_rate=tax_rate,
                status=status or ProductStatus.ACTIVE,
            )

            AuditLogService.record(
                action=AuditAction.CREATE,
                entity_type="product",
                entity_id=product.id,
                company_id=company.id,
                actor_user=actor_user,
                after_state=_product_audit_state(product),
                request=request,
            )

            return product

    @classmethod
    def update_product(
        cls,
        product_id: str | uuid.UUID,
        validated_data: Dict[str, Any],
        company_id: Optional[str | uuid.UUID] = None,
        actor_user: Any = None,
        request: Any = None,
    ) -> Product:
        """
        Update an existing Product. `subcategory` is not editable here —
        not documented as a supported reassignment anywhere (mirrors
        ProjectService.update_project's exclusion of `client` for the same
        reasoning: set at creation, not casually reassigned via edit).

        Orphan cleanup (BE-078): when `image_url` changes (replaced with a
        new image, or cleared entirely), the previously-stored image is
        deleted from object storage -- but ONLY when this app actually
        owns that file, i.e. the product's *current* `image_storage_key`
        (captured before the overwrite) is non-blank. A blank key means
        the existing `image_url` was either never set or was entered
        manually via the alternate URL-entry flow -- in either case this
        app has no storage key to delete and must never guess one from
        the URL itself (an arbitrary external URL could coincidentally
        collide with a real storage key on the same backend). The delete
        is deferred to `transaction.on_commit` so a superseded file is
        never destroyed unless the new Product state actually committed
        successfully (BE-078 §15: never delete the old valid object before
        the new DB state is committed).
        """
        with transaction.atomic():
            product = cls.get_product_by_id(product_id, company_id=company_id)
            before_state = _product_audit_state(product)
            previous_image_key = product.image_storage_key

            fields: Dict[str, Any] = {}

            if "name" in validated_data:
                fields["name"] = validators.require_product_name(validated_data["name"])

            if "image_url" in validated_data:
                fields["image_url"] = validated_data["image_url"] or ""
                # A new imageUrl always resets the key too: either the
                # caller supplied a fresh imageStorageKey (a real upload)
                # or it defaults to "" (manual URL entry / explicit
                # removal) -- image_url and image_storage_key must never
                # drift out of sync with each other.
                fields["image_storage_key"] = validated_data.get("image_storage_key") or ""

            if "unit" in validated_data:
                fields["unit"] = validated_data["unit"] or ""

            for field in ("default_cost", "default_selling_rate", "tax_rate"):
                if field in validated_data:
                    fields[field] = validated_data[field]

            if "status" in validated_data:
                fields["status"] = validated_data["status"]

            product = ProductRepository.save(product, fields)

            if "image_url" in validated_data and previous_image_key:
                new_image_key = fields.get("image_storage_key", "")
                if previous_image_key != new_image_key:
                    transaction.on_commit(
                        lambda key=previous_image_key: storage_service.delete_file("products", key)
                    )

            AuditLogService.record(
                action=AuditAction.UPDATE,
                entity_type="product",
                entity_id=product.id,
                company_id=product.company_id,
                actor_user=actor_user,
                before_state=before_state,
                after_state=_product_audit_state(product),
                request=request,
            )

            return product

    @classmethod
    def soft_delete_product(
        cls,
        product_id: str | uuid.UUID,
        company_id: Optional[str | uuid.UUID] = None,
        actor_user: Any = None,
        request: Any = None,
    ) -> None:
        """
        Soft-delete a Product by setting deleted_at timestamp. No further
        delete guard needed -- Product is the leaf of the catalog
        hierarchy (nothing in this sprint's scope references it yet;
        boq_item.product_id is a later sprint's concern).
        """
        with transaction.atomic():
            product = cls.get_product_by_id(product_id, company_id=company_id)
            product_id_val = product.id
            company_id_val = product.company_id
            before_state = _product_audit_state(product)

            ProductRepository.soft_delete(product)

            AuditLogService.record(
                action=AuditAction.DELETE,
                entity_type="product",
                entity_id=product_id_val,
                company_id=company_id_val,
                actor_user=actor_user,
                before_state=before_state,
                request=request,
            )


class ProductImageService:
    """
    Stores a validated product image via the shared storage abstraction
    (`apps.common.storage` — PUBLIC scope "products"; `FileSystemStorage`
    against `MEDIA_ROOT` in development today, swappable to S3/object
    storage later purely via `STORAGE_BACKEND`, with no business-logic
    change here) and returns a URL (persisted through the ordinary
    `Product.imageUrl` field) plus the storage `key` (persisted through
    the internal-only `Product.imageStorageKey` field, BE-078) so a later
    replace/remove can clean up this exact file. Deliberately has no model
    of its own — an uploaded image is not a first-class tenant entity the
    way Document is; it is a blob a Product's own `imageUrl` field ends up
    referencing.
    """

    @classmethod
    def upload_image(
        cls,
        company_id: str | uuid.UUID,
        uploaded_file: Any,
        request: Any = None,
    ) -> Dict[str, Any]:
        extension, content_type = validators.validate_product_image(uploaded_file)

        storage_key = storage_service.generate_storage_key("products", company_id, extension)
        storage_service.save_upload("products", storage_key, uploaded_file)
        url = storage_service.public_url("products", storage_key, request=request)

        return {
            "url": url,
            "key": storage_key,
            "fileName": storage_service.safe_display_filename(getattr(uploaded_file, "name", "")),
            "contentType": content_type,
            "size": uploaded_file.size,
        }
