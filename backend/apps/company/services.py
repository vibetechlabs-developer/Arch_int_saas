import uuid
from typing import Any, Dict, Optional
from django.db import transaction
from django.db.models import QuerySet

from apps.audit.models import AuditAction
from apps.audit.services import AuditLogService
from apps.common import storage as storage_service
from apps.company import selectors, validators
from apps.company.models import Company
from apps.company.repositories import CompanyRepository

AUDITED_FIELDS = ("name", "status", "currency", "gst_number", "logo_url", "settings")


def _audit_snapshot(company: Company) -> Dict[str, Any]:
    return {field: getattr(company, field) for field in AUDITED_FIELDS}


class CompanyService:
    """
    Business logic and orchestration service for Company tenants.
    Adheres to Folder_Structure.md §2: controllers contain no business logic;
    all data operations and validations run through CompanyService, which in
    turn delegates persistence to CompanyRepository, read/list queries to
    apps.company.selectors, and input normalization to apps.company.validators.
    """

    @classmethod
    def create_company(
        cls,
        name: str,
        currency: str = "INR",
        gst_number: Optional[str] = None,
        status: str = "trial",
        settings: Optional[Dict[str, Any]] = None,
        actor_user: Any = None,
        request: Any = None,
    ) -> Company:
        """
        Create a new Company tenant.

        Also auto-seeds the documented default roles (BE-049/§3) via
        apps.users.services.RoleService.seed_default_roles_for_company() so
        a new tenant isn't empty-handed. Imported locally (not at module
        level) to avoid a load-order dependency between apps.company and
        apps.users during Django app registry population — apps.users
        already imports apps.company.models at module level, so a
        module-level import here in the other direction would risk a
        circular/partial-import at startup.
        """
        with transaction.atomic():
            fields = validators.build_create_fields(name, currency, gst_number, status, settings)
            company = CompanyRepository.create(**fields)

            from apps.users.services import RoleService

            RoleService.seed_default_roles_for_company(company)

            AuditLogService.record(
                action=AuditAction.CREATE,
                entity_type="company",
                entity_id=company.id,
                company_id=company.id,
                actor_user=actor_user,
                after_state=_audit_snapshot(company),
                request=request,
            )

            return company

    @classmethod
    def get_company_by_id(cls, company_id: str | uuid.UUID) -> Company:
        """
        Retrieve an active, non-deleted Company by primary key UUID.
        Raises NotFound if company does not exist or is soft-deleted.
        """
        return CompanyRepository.get_by_id(company_id)

    @classmethod
    def list_companies(
        cls,
        status: Optional[str] = None,
        search: Optional[str] = None,
        ordering: str = "-created_at",
    ) -> QuerySet[Company]:
        """
        List active companies with optional status filtering and search.
        """
        return selectors.list_companies(status=status, search=search, ordering=ordering)

    @classmethod
    def update_company(
        cls,
        company_id: str | uuid.UUID,
        validated_data: Dict[str, Any],
        is_platform_admin: bool = False,
        actor_user: Any = None,
        request: Any = None,
    ) -> Company:
        """
        Update an existing Company tenant.
        Only Platform Admins are allowed to alter tenant status.

        Recorded as a single AuditAction.UPDATE entry regardless of which
        fields changed — a status change is not a distinct action type
        (03_Database/Database_Schema.md's documented action set is just
        create/update/delete/approve), it's simply visible as the "status"
        key differing between before_state and after_state.
        """
        with transaction.atomic():
            company = cls.get_company_by_id(company_id)
            before_state = _audit_snapshot(company)
            previous_logo_key = company.logo_storage_key

            fields = validators.build_update_fields(
                validated_data, company.settings, is_platform_admin
            )
            company = CompanyRepository.save(company, fields)

            # Orphan cleanup (BE-078), mirroring
            # ProductService.update_product exactly: only ever delete a
            # file this app actually owns (a non-blank previous key), and
            # only after the new state has actually committed.
            if "logo_url" in validated_data and previous_logo_key:
                new_logo_key = fields.get("logo_storage_key", "")
                if previous_logo_key != new_logo_key:
                    transaction.on_commit(
                        lambda key=previous_logo_key: storage_service.delete_file("companies", key)
                    )

            AuditLogService.record(
                action=AuditAction.UPDATE,
                entity_type="company",
                entity_id=company.id,
                company_id=company.id,
                actor_user=actor_user,
                before_state=before_state,
                after_state=_audit_snapshot(company),
                request=request,
            )

            return company

    @classmethod
    def upload_logo(
        cls,
        company_id: str | uuid.UUID,
        uploaded_file: Any,
        request: Any = None,
    ) -> Dict[str, Any]:
        """
        Stores a validated company logo via the shared storage
        abstraction (BE-078, PUBLIC scope "companies") and returns a URL
        (persisted through `Company.logoUrl`) plus the storage `key`
        (persisted through the internal-only `Company.logoStorageKey`) so
        a later replace/remove can clean up this exact file. Mirrors
        `apps.products.services.ProductImageService.upload_image` exactly
        -- deliberately decoupled from `update_company` (the caller
        PATCHes the company with the returned url+key immediately after),
        the same two-step pattern Product images already established.
        """
        from apps.common.storage import validate_image_upload

        extension, content_type = validate_image_upload(uploaded_file)

        storage_key = storage_service.generate_storage_key("companies", company_id, extension)
        storage_service.save_upload("companies", storage_key, uploaded_file)
        url = storage_service.public_url("companies", storage_key, request=request)

        return {
            "url": url,
            "key": storage_key,
            "fileName": storage_service.safe_display_filename(getattr(uploaded_file, "name", "")),
            "contentType": content_type,
            "size": uploaded_file.size,
        }

    @classmethod
    def soft_delete_company(
        cls,
        company_id: str | uuid.UUID,
        actor_user: Any = None,
        request: Any = None,
    ) -> None:
        """
        Soft-delete a Company tenant by setting deleted_at timestamp.
        """
        with transaction.atomic():
            company = cls.get_company_by_id(company_id)
            before_state = _audit_snapshot(company)
            company_id_val = company.id

            CompanyRepository.soft_delete(company)

            AuditLogService.record(
                action=AuditAction.DELETE,
                entity_type="company",
                entity_id=company_id_val,
                company_id=company_id_val,
                actor_user=actor_user,
                before_state=before_state,
                request=request,
            )
