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
from apps.users.models import CompanyMembership, CompanyMembershipStatus, Role
from apps.users.permission_catalog import ALL_PERMISSION_CODES, DEFAULT_ROLE_PERMISSIONS
from apps.users.repositories import (
    CompanyMembershipRepository,
    PermissionRepository,
    RolePermissionRepository,
    RoleRepository,
)

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

    @classmethod
    def assign_permissions(
        cls,
        role_id: str | uuid.UUID,
        codes: list[str],
        company_id: Optional[str | uuid.UUID] = None,
        actor_user: Any = None,
        actor_membership: Optional[CompanyMembership] = None,
        request: Any = None,
    ) -> Role:
        """
        Replace a role's permission grants with exactly the given set of
        permission codes (BE-049/BE-051). Unknown codes are rejected rather
        than silently ignored, since a typo'd code would otherwise grant
        nothing while looking like it succeeded.

        Privilege-escalation guard (BE-054 §12): a non-platform-admin actor
        (identified by passing `actor_membership`) can never grant a role
        permission codes beyond their own — otherwise a `role.manage`
        holder could hand a role (including their own) codes they don't
        themselves possess. `actor_membership=None` means the caller is a
        platform admin (who has no CompanyMembership to check against) and
        is exempt, per the standing platform-admin bypass.
        """
        with transaction.atomic():
            role = cls.get_role_by_id(role_id, company_id=company_id)

            before_codes = sorted(PermissionRepository.codes_for_role(role.id))

            permissions = list(PermissionRepository.filter_by_codes(codes))
            found_codes = {p.code for p in permissions}
            unknown_codes = sorted(set(codes) - found_codes)
            if unknown_codes:
                raise drf_exceptions.ValidationError(
                    {"permissionCodes": [f"Unknown permission code(s): {', '.join(unknown_codes)}"]}
                )

            if actor_membership is not None:
                actor_codes = PermissionService.get_permission_codes_for_membership(actor_membership)
                escalating_codes = sorted(found_codes - actor_codes)
                if escalating_codes:
                    raise drf_exceptions.PermissionDenied(
                        "Cannot grant a role permissions you do not hold yourself: "
                        f"{', '.join(escalating_codes)}"
                    )

            RolePermissionRepository.replace_role_permissions(role, permissions)
            after_codes = sorted(found_codes)

            AuditLogService.record(
                action=AuditAction.UPDATE,
                entity_type="role_permission",
                entity_id=role.id,
                company_id=role.company_id,
                actor_user=actor_user,
                before_state={"permission_codes": before_codes},
                after_state={"permission_codes": after_codes},
                request=request,
            )

            return role

    @classmethod
    def seed_default_roles_for_company(cls, company: Any) -> list[Role]:
        """
        Auto-create the documented default roles (05_Security/Permissions.md
        §3) for a newly created company, each with its representative
        permission set from apps.users.permission_catalog. Called from
        apps.company.services.CompanyService.create_company() so a new
        tenant isn't empty-handed. Company Admins can still edit, rename, or
        add roles afterward via the existing /roles API — this is a
        starting point, not a locked-in set.

        Not backfilled onto companies that existed before this feature
        shipped; only new companies get auto-seeded roles.
        """
        all_permissions_by_code = {p.code: p for p in PermissionRepository.all()}
        created_roles: list[Role] = []

        for role_name, codes in DEFAULT_ROLE_PERMISSIONS.items():
            role = RoleRepository.create(
                company=company,
                name=role_name,
                description=f"Default '{role_name}' role, auto-created for this company.",
                is_active=True,
            )

            resolved_codes = ALL_PERMISSION_CODES if codes == "__all__" else codes
            permissions = [
                all_permissions_by_code[code]
                for code in resolved_codes
                if code in all_permissions_by_code
            ]
            RolePermissionRepository.replace_role_permissions(role, permissions)
            created_roles.append(role)

        return created_roles


class PermissionService:
    """
    Read-only RBAC resolution, wired into the shared
    `apps.common.permissions.TenantScopedPermission` as of BE-054.
    """

    @staticmethod
    def list_all_permissions():
        return PermissionRepository.all()

    @staticmethod
    def get_permission_codes_for_membership(membership: Optional[CompanyMembership]) -> set[str]:
        """
        A membership with no role, an inactive role, no active membership
        status, or that is None has no permission codes — fails closed
        rather than defaulting to "every code" or "every code the company
        has ever granted".
        """
        if membership is None:
            return set()
        if membership.status != CompanyMembershipStatus.ACTIVE:
            return set()
        if membership.role_id is None:
            return set()
        # `membership.role` relies on the caller having select_related'd
        # it (apps.common.permissions.get_active_membership_for_request
        # does) — falls back to a query otherwise, never raises.
        if membership.role is None or not membership.role.is_active:
            return set()
        return PermissionRepository.codes_for_role(membership.role_id)

    @staticmethod
    def has_permission(membership: Optional[CompanyMembership], code: str) -> bool:
        return code in PermissionService.get_permission_codes_for_membership(membership)


class CompanyMembershipService:
    """
    Business logic and orchestration service for CompanyMembership
    management (BE-052): invite, list, remove, suspend, reactivate, and
    assign/change role. Every mutation is audited (BE-055).
    """

    @classmethod
    def list_memberships(
        cls,
        company_id: str | uuid.UUID,
        status: Optional[str] = None,
        search: Optional[str] = None,
        ordering: str = "-created_at",
    ):
        return selectors.list_memberships_for_company(
            company_id=company_id, status=status, search=search, ordering=ordering
        )

    @classmethod
    def list_my_memberships(cls, user_id: str | uuid.UUID):
        """
        BE-053: the current user's own active memberships across every
        company they belong to, for workspace switching.
        """
        return selectors.list_memberships_for_user(user_id)

    @classmethod
    def get_membership_by_id(
        cls,
        membership_id: str | uuid.UUID,
        company_id: Optional[str | uuid.UUID] = None,
    ) -> CompanyMembership:
        membership = CompanyMembershipRepository.get_by_id(membership_id)
        if company_id is not None and str(membership.company_id) != str(company_id):
            raise drf_exceptions.NotFound("The requested membership was not found.")
        return membership

    @classmethod
    def invite_member(
        cls,
        company_id: str | uuid.UUID,
        email: str,
        role_id: Optional[str | uuid.UUID],
        actor_user: Any = None,
        actor_membership: Optional[CompanyMembership] = None,
        request: Any = None,
    ) -> CompanyMembership:
        """
        Invite an existing user (by email) into a company. This does not
        create a new User account — matches CLAUDE.md's `User -> Company
        Membership` model, where a user is a global identity that can be
        invited into a company it doesn't yet belong to. Creating a brand
        new user record for an email with no existing account is a
        registration/onboarding flow, out of this task's scope.

        `role_id` is now required (BE-054 §1): a new membership silently
        left with no role would have zero permission codes under
        enforcement, which is a confusing dead end for whoever invited
        them — the product has no defined default role, so the caller
        must pick one explicitly rather than the platform guessing.

        Privilege-escalation guard (BE-054 §12): mirrors
        RoleService.assign_permissions — a non-platform-admin actor
        (`actor_membership` given) can't invite someone directly into a
        role that grants permission codes the actor doesn't hold.
        """
        with transaction.atomic():
            company = RoleRepository.get_company_by_id(company_id)
            cleaned_email = validators.clean_email(email)
            user = CompanyMembershipRepository.get_user_by_email(cleaned_email)

            if CompanyMembershipRepository.active_membership_exists(company.id, user.id):
                raise ConflictError("This user already has a membership in this company.")

            if not role_id:
                raise drf_exceptions.ValidationError(
                    {"roleId": ["A role must be explicitly selected when inviting a member."]}
                )

            role = CompanyMembershipRepository.get_role_by_id(role_id)
            validators.validate_role_belongs_to_company(role, company.id)
            validators.validate_role_is_active(role)

            if actor_membership is not None:
                actor_codes = PermissionService.get_permission_codes_for_membership(actor_membership)
                role_codes = PermissionRepository.codes_for_role(role.id)
                escalating_codes = sorted(role_codes - actor_codes)
                if escalating_codes:
                    raise drf_exceptions.PermissionDenied(
                        "Cannot invite a member into a role granting permissions you do not "
                        f"hold yourself: {', '.join(escalating_codes)}"
                    )

            try:
                with transaction.atomic():
                    membership = CompanyMembershipRepository.create(
                        company=company,
                        user=user,
                        role=role,
                        status=CompanyMembershipStatus.INVITED,
                    )
            except IntegrityError as exc:
                raise ConflictError(
                    "This user already has a membership in this company."
                ) from exc

            AuditLogService.record(
                action=AuditAction.CREATE,
                entity_type="company_membership",
                entity_id=membership.id,
                company_id=company.id,
                actor_user=actor_user,
                after_state={
                    "user_id": str(user.id),
                    "role_id": str(role.id) if role else None,
                    "status": membership.status,
                },
                request=request,
            )

            return membership

    @classmethod
    def _membership_snapshot(cls, membership: CompanyMembership) -> Dict[str, Any]:
        return {
            "user_id": str(membership.user_id),
            "role_id": str(membership.role_id) if membership.role_id else None,
            "status": membership.status,
        }

    @classmethod
    def assign_role(
        cls,
        membership_id: str | uuid.UUID,
        role_id: Optional[str | uuid.UUID],
        company_id: Optional[str | uuid.UUID] = None,
        actor_user: Any = None,
        actor_membership: Optional[CompanyMembership] = None,
        request: Any = None,
    ) -> CompanyMembership:
        """
        Assign, change, or clear (role_id=None) a membership's role.

        Privilege-escalation guard (BE-054 §12/#10): clearing a role
        (role_id=None) only ever removes access, so it's exempt from the
        check below. Assigning/changing a role is guarded the same way as
        RoleService.assign_permissions/invite_member — a non-platform-admin
        actor can't grant a role whose permission codes exceed their own,
        which also directly prevents self-escalation through a crafted
        roleId (BE-054 §10/#O): an actor can never assign themselves (or
        anyone else) a role more powerful than their own.
        """
        with transaction.atomic():
            membership = cls.get_membership_by_id(membership_id, company_id=company_id)
            before_state = cls._membership_snapshot(membership)

            role = None
            if role_id is not None:
                role = CompanyMembershipRepository.get_role_by_id(role_id)
                validators.validate_role_belongs_to_company(role, membership.company_id)
                validators.validate_role_is_active(role)

                if actor_membership is not None:
                    actor_codes = PermissionService.get_permission_codes_for_membership(
                        actor_membership
                    )
                    role_codes = PermissionRepository.codes_for_role(role.id)
                    escalating_codes = sorted(role_codes - actor_codes)
                    if escalating_codes:
                        raise drf_exceptions.PermissionDenied(
                            "Cannot assign a role granting permissions you do not hold "
                            f"yourself: {', '.join(escalating_codes)}"
                        )

            membership = CompanyMembershipRepository.save(membership, {"role": role})

            AuditLogService.record(
                action=AuditAction.UPDATE,
                entity_type="company_membership",
                entity_id=membership.id,
                company_id=membership.company_id,
                actor_user=actor_user,
                before_state=before_state,
                after_state=cls._membership_snapshot(membership),
                request=request,
            )

            return membership

    @classmethod
    def _set_status(
        cls,
        membership_id: str | uuid.UUID,
        new_status: str,
        company_id: Optional[str | uuid.UUID],
        actor_user: Any,
        request: Any,
    ) -> CompanyMembership:
        with transaction.atomic():
            membership = cls.get_membership_by_id(membership_id, company_id=company_id)
            before_state = cls._membership_snapshot(membership)

            membership = CompanyMembershipRepository.save(membership, {"status": new_status})

            AuditLogService.record(
                action=AuditAction.UPDATE,
                entity_type="company_membership",
                entity_id=membership.id,
                company_id=membership.company_id,
                actor_user=actor_user,
                before_state=before_state,
                after_state=cls._membership_snapshot(membership),
                request=request,
            )

            return membership

    @classmethod
    def suspend_member(
        cls,
        membership_id: str | uuid.UUID,
        company_id: Optional[str | uuid.UUID] = None,
        actor_user: Any = None,
        request: Any = None,
    ) -> CompanyMembership:
        return cls._set_status(
            membership_id, CompanyMembershipStatus.REVOKED, company_id, actor_user, request
        )

    @classmethod
    def reactivate_member(
        cls,
        membership_id: str | uuid.UUID,
        company_id: Optional[str | uuid.UUID] = None,
        actor_user: Any = None,
        request: Any = None,
    ) -> CompanyMembership:
        return cls._set_status(
            membership_id, CompanyMembershipStatus.ACTIVE, company_id, actor_user, request
        )

    @classmethod
    def remove_member(
        cls,
        membership_id: str | uuid.UUID,
        company_id: Optional[str | uuid.UUID] = None,
        actor_user: Any = None,
        request: Any = None,
    ) -> None:
        with transaction.atomic():
            membership = cls.get_membership_by_id(membership_id, company_id=company_id)
            membership_id_val = membership.id
            company_id_val = membership.company_id
            before_state = cls._membership_snapshot(membership)

            CompanyMembershipRepository.soft_delete(membership)

            AuditLogService.record(
                action=AuditAction.DELETE,
                entity_type="company_membership",
                entity_id=membership_id_val,
                company_id=company_id_val,
                actor_user=actor_user,
                before_state=before_state,
                request=request,
            )
