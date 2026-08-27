import logging
import uuid
from typing import Any, Dict, Optional
from django.db import IntegrityError, transaction
from django.db.models import QuerySet
from rest_framework import exceptions as drf_exceptions

from apps.audit.models import AuditAction
from apps.audit.services import AuditLogService
from apps.common.exceptions import ConflictError
from apps.users import selectors, validators
from apps.users.models import Role
from apps.users.repositories import RoleRepository

logger = logging.getLogger("apps.users.services")


class RoleService:
    """
    Business logic and orchestration service for Role management.
    Adheres to Folder_Structure.md §2: controllers contain no business logic;
    all data operations and validations run through RoleService, which in
    turn delegates persistence to RoleRepository, read/list queries to
    apps.users.selectors, and input normalization to apps.users.validators.
    """

    @classmethod
    def list_roles(
        cls,
        company_id: Optional[str | uuid.UUID] = None,
        is_active: Optional[bool] = None,
        search: Optional[str] = None,
        ordering: str = "-created_at",
    ) -> QuerySet[Role]:
        """
        List active (non-soft-deleted) roles with optional tenant scoping,
        status filtering, search, and ordering.

        company_id=None means "no tenant filter" — reachable only from the
        Platform Admin surface (RoleViewSet never calls this without a
        resolved request.company_id for a non-admin, per BE-021 and
        Tenant.md §4's ban on a "list across companies" mode for a
        company-scoped resource).
        """
        return selectors.list_roles(
            company_id=company_id,
            is_active=is_active,
            search=search,
            ordering=ordering,
        )

    @classmethod
    def list_roles_for_viewer(
        cls,
        is_platform_admin: bool,
        resolved_company_id: Optional[str | uuid.UUID],
        admin_company_id_param: Optional[str],
        is_active: Optional[bool] = None,
        search: Optional[str] = None,
        ordering: str = "-created_at",
    ) -> QuerySet[Role]:
        """
        Resolve which company_id list_roles() filters by, given the caller's
        admin status (RoleViewSet.list() orchestrates only — this decision
        used to live inline in the view).

        Platform Admin: filters by whatever companyId query param was
        supplied (None = every company, the one case where "no tenant
        filter" is legitimate — the Platform Admin surface is structurally
        separate per Tenant.md §6).

        Non-admin: always resolved_company_id — the single company
        TenantJWTAuthentication already resolved and validated for this
        request (BE-021). Never re-derived from anything else.
        """
        if is_platform_admin:
            return cls.list_roles(
                company_id=admin_company_id_param,
                is_active=is_active,
                search=search,
                ordering=ordering,
            )

        return cls.list_roles(
            company_id=resolved_company_id,
            is_active=is_active,
            search=search,
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
        Resolve which company a new Role is created in, given the caller's
        admin status and any client-supplied companyId (RoleViewSet.create()
        orchestrates only — this decision used to live inline in the view).

        Platform Admin: companyId is required and explicit (no request-
        resolved company exists for an admin token).

        Non-admin: always resolved_company_id — the single company
        TenantJWTAuthentication already resolved and validated for this
        request (BE-021). A client-supplied companyId is never trusted as
        the authorization boundary (Tenant.md §4): if present, it must
        match resolved_company_id exactly, or the request is rejected
        outright rather than silently overridden.
        """
        if is_platform_admin:
            if not supplied_company_id:
                raise drf_exceptions.ValidationError(
                    {"companyId": ["companyId is required for platform admin role creation."]}
                )
            return supplied_company_id

        if supplied_company_id and str(supplied_company_id) != str(resolved_company_id):
            raise drf_exceptions.PermissionDenied(
                "You do not have permission to create roles for this company."
            )
        return resolved_company_id

    @classmethod
    def get_role_by_id(
        cls,
        role_id: str | uuid.UUID,
        company_id: Optional[str | uuid.UUID] = None,
    ) -> Role:
        """
        Retrieve an active, non-deleted Role by primary key UUID.
        Raises NotFound if role does not exist, is soft-deleted, or belongs to another company.
        """
        role = RoleRepository.get_by_id(role_id)

        if company_id is not None and str(role.company_id) != str(company_id):
            raise drf_exceptions.NotFound("The requested role was not found.")

        return role

    @classmethod
    def create_role(
        cls,
        company_id: str | uuid.UUID,
        name: str,
        description: str = "",
        is_active: bool = True,
        actor_user: Any = None,
        request: Any = None,
    ) -> Role:
        """
        Create a new Role within a Company tenant.
        Enforces name uniqueness per company among active records and transaction atomicity.

        The name_exists_for_company() check above is a TOCTOU race under
        concurrent requests — two callers can both pass it before either
        commits. The database's own unique_active_role_per_company
        constraint (apps/users/models.py) is the real backstop: a
        concurrent collision raises IntegrityError here, which is caught
        and converted to the same ConflictError (409) the pre-check raises,
        instead of propagating as an unhandled 500. Scoped to a nested
        atomic() (savepoint) so the failed insert rolls back on its own
        without aborting the outer transaction this method already runs in.
        """
        with transaction.atomic():
            company = RoleRepository.get_company_by_id(company_id)
            cleaned_name = validators.clean_role_name(name)

            if RoleRepository.name_exists_for_company(company.id, cleaned_name):
                raise ConflictError("A role with this name already exists for this company.")

            try:
                with transaction.atomic():
                    role = RoleRepository.create(
                        company=company,
                        name=cleaned_name,
                        description=validators.clean_role_description(description),
                        is_active=is_active,
                    )
            except IntegrityError as exc:
                raise ConflictError(
                    "A role with this name already exists for this company."
                ) from exc

            AuditLogService.record(
                action=AuditAction.CREATE,
                entity_type="role",
                entity_id=role.id,
                company_id=company.id,
                actor_user=actor_user,
                after_state={
                    "name": role.name,
                    "description": role.description,
                    "is_active": role.is_active,
                },
                request=request,
            )

            return role

    @classmethod
    def update_role(
        cls,
        role_id: str | uuid.UUID,
        validated_data: Dict[str, Any],
        company_id: Optional[str | uuid.UUID] = None,
        actor_user: Any = None,
        request: Any = None,
    ) -> Role:
        """
        Update an existing Role within a Company tenant.
        Enforces name uniqueness and transaction atomicity.

        Same TOCTOU race as create_role() applies to a concurrent rename:
        the name_exists_for_company() pre-check can pass for two concurrent
        callers before either commits. The database constraint is the real
        backstop; a concurrent collision raises IntegrityError, caught here
        and converted to the same ConflictError (409) the pre-check raises.
        """
        with transaction.atomic():
            role = cls.get_role_by_id(role_id, company_id=company_id)
            old_value = {
                "name": role.name,
                "description": role.description,
                "is_active": role.is_active,
            }

            fields: Dict[str, Any] = {}

            if "name" in validated_data:
                new_name = validators.clean_role_name(validated_data["name"])
                if new_name.lower() != role.name.lower():
                    if RoleRepository.name_exists_for_company(
                        role.company_id, new_name, exclude_id=role.id
                    ):
                        raise ConflictError("A role with this name already exists for this company.")
                fields["name"] = new_name

            if "description" in validated_data:
                fields["description"] = validators.clean_role_description(
                    validated_data["description"]
                )

            if "is_active" in validated_data:
                fields["is_active"] = validated_data["is_active"]

            try:
                with transaction.atomic():
                    role = RoleRepository.save(role, fields)
            except IntegrityError as exc:
                raise ConflictError(
                    "A role with this name already exists for this company."
                ) from exc

            AuditLogService.record(
                action=AuditAction.UPDATE,
                entity_type="role",
                entity_id=role.id,
                company_id=role.company_id,
                actor_user=actor_user,
                before_state=old_value,
                after_state={
                    "name": role.name,
                    "description": role.description,
                    "is_active": role.is_active,
                },
                request=request,
            )

            return role

    @classmethod
    def soft_delete_role(
        cls,
        role_id: str | uuid.UUID,
        company_id: Optional[str | uuid.UUID] = None,
        actor_user: Any = None,
        request: Any = None,
    ) -> None:
        """
        Soft-delete a Role by setting deleted_at timestamp.
        """
        with transaction.atomic():
            role = cls.get_role_by_id(role_id, company_id=company_id)
            role_id_val = role.id
            company_id_val = role.company_id
            before_state = {
                "name": role.name,
                "description": role.description,
                "is_active": role.is_active,
            }

            RoleRepository.soft_delete(role)

            AuditLogService.record(
                action=AuditAction.DELETE,
                entity_type="role",
                entity_id=role_id_val,
                company_id=company_id_val,
                actor_user=actor_user,
                before_state=before_state,
                request=request,
            )
