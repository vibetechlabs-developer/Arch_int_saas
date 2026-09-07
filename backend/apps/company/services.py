import uuid
from typing import Any, Dict, Optional
from django.db import transaction
from django.db.models import QuerySet

from apps.audit.models import AuditAction
from apps.audit.services import AuditLogService
from apps.company import selectors, validators
from apps.company.models import Company
from apps.company.repositories import CompanyRepository

AUDITED_FIELDS = ("name", "status", "currency", "gst_number", "settings")


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

            fields = validators.build_update_fields(
                validated_data, company.settings, is_platform_admin
            )
            company = CompanyRepository.save(company, fields)

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
