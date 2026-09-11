import uuid
from typing import Any, Dict, Optional

from django.db.models import QuerySet
from rest_framework import exceptions as drf_exceptions

from apps.company.models import Company
from apps.users.models import (
    CompanyMembership,
    CompanyMembershipStatus,
    Permission,
    Role,
    RolePermission,
    User,
)


class RoleRepository:
    """
    Data-access layer for Role. Owns all direct ORM reads/writes so
    RoleService stays free of persistence details (BACKEND_RULES.md:
    View -> Serializer -> Service -> Repository -> Model).
    """

    @staticmethod
    def all() -> QuerySet[Role]:
        return Role.objects.select_related("company").all()

    @staticmethod
    def get_by_id(role_id: str | uuid.UUID) -> Role:
        try:
            return Role.objects.select_related("company").get(id=role_id)
        except (Role.DoesNotExist, ValueError):
            raise drf_exceptions.NotFound("The requested role was not found.")

    @staticmethod
    def name_exists_for_company(
        company_id: str | uuid.UUID,
        name: str,
        exclude_id: Optional[str | uuid.UUID] = None,
    ) -> bool:
        queryset = Role.objects.filter(company_id=company_id, name__iexact=name)
        if exclude_id is not None:
            queryset = queryset.exclude(id=exclude_id)
        return queryset.exists()

    @staticmethod
    def get_by_system_key(company_id: str | uuid.UUID, system_key: str) -> Optional[Role]:
        """
        BE-069: resolve a company's system role by its stable identity,
        never by display name. Returns None rather than raising -- a
        company predating the seeding feature may genuinely have no
        Owner-system-key role at all (see RoleService.
        seed_default_roles_for_company's own "not backfilled onto
        existing companies" note), which callers must be able to treat as
        "no system role of this kind exists here" rather than an error.
        """
        return Role.objects.filter(company_id=company_id, system_key=system_key).first()

    @staticmethod
    def create(**fields: Any) -> Role:
        return Role.objects.create(**fields)

    @staticmethod
    def save(role: Role, fields: Optional[Dict[str, Any]] = None) -> Role:
        for field, value in (fields or {}).items():
            setattr(role, field, value)
        role.save()
        return role

    @staticmethod
    def soft_delete(role: Role) -> None:
        role.delete()

    @staticmethod
    def unassign_from_memberships(role_id: str | uuid.UUID) -> int:
        """
        Clear the role FK (set to null) on every membership currently
        pointing at role_id. Soft-deleting a Role never triggers Django's
        on_delete=SET_NULL collector — that only fires on a real DB DELETE
        — so without this, a membership keeps referencing a role that no
        longer appears anywhere in the Roles API, and (per
        PermissionService.get_permission_codes_for_membership, which keys
        off role.is_active rather than role.deleted_at) keeps its full
        permission grant indefinitely. Explicitly replicating the FK's own
        declared SET_NULL intent here closes that gap: a membership left
        without a role is already the documented, tested, fail-closed
        "zero permission codes" state used elsewhere in this module.
        Returns the number of memberships affected, for audit logging.
        """
        return CompanyMembership.objects.filter(role_id=role_id).update(role=None)

    @staticmethod
    def get_company_by_id(company_id: str | uuid.UUID) -> Company:
        try:
            return Company.objects.get(id=company_id)
        except (Company.DoesNotExist, ValueError):
            raise drf_exceptions.NotFound("The specified company was not found.")


class PermissionRepository:
    """
    Data-access layer for the global Permission catalog. Read-mostly — the
    catalog is seeded via a data migration (0005), not created through the
    application at runtime.
    """

    @staticmethod
    def all() -> QuerySet[Permission]:
        return Permission.objects.all()

    @staticmethod
    def codes_for_role(role_id: str | uuid.UUID) -> set[str]:
        """
        A role's active (non-soft-deleted) permission codes.

        Deliberately queries RolePermission.objects (its soft-delete-aware
        default manager) for the permission ids, then Permission.objects for
        the codes -- rather than
        `Permission.objects.filter(role_permissions__role_id=role_id)`,
        which performs a raw SQL join across the relation and does NOT
        respect RolePermission's soft-delete manager, so a soft-deleted
        grant would still be counted as active.
        """
        permission_ids = RolePermission.objects.filter(role_id=role_id).values_list(
            "permission_id", flat=True
        )
        return set(Permission.objects.filter(id__in=permission_ids).values_list("code", flat=True))

    @staticmethod
    def filter_by_codes(codes: list[str]) -> QuerySet[Permission]:
        return Permission.objects.filter(code__in=codes)


class RolePermissionRepository:
    """
    Data-access layer for Role <-> Permission grants.
    """

    @staticmethod
    def replace_role_permissions(role: Role, permissions: list[Permission]) -> None:
        """
        Set a role's permission grants to exactly the given set: soft-deletes
        any existing grant not in the new set, and creates any grant that
        doesn't already exist (rather than delete-then-recreate everything,
        which would needlessly churn created_at/audit-adjacent rows).
        """
        existing = {
            rp.permission_id: rp
            for rp in RolePermission.objects.filter(role=role)
        }
        target_ids = {p.id for p in permissions}

        for permission_id, row in existing.items():
            if permission_id not in target_ids:
                row.delete()

        existing_ids = set(existing.keys())
        RolePermission.objects.bulk_create(
            [
                RolePermission(role=role, permission=permission)
                for permission in permissions
                if permission.id not in existing_ids
            ]
        )

    @staticmethod
    def grant(role: Role, permission: Permission) -> RolePermission:
        return RolePermission.objects.get_or_create(role=role, permission=permission)[0]


class CompanyMembershipRepository:
    """
    Data-access layer for CompanyMembership.
    """

    @staticmethod
    def all() -> QuerySet[CompanyMembership]:
        return CompanyMembership.objects.select_related("company", "user", "role")

    @staticmethod
    def get_by_id(membership_id: str | uuid.UUID) -> CompanyMembership:
        try:
            return CompanyMembershipRepository.all().get(id=membership_id)
        except (CompanyMembership.DoesNotExist, ValueError):
            raise drf_exceptions.NotFound("The requested membership was not found.")

    @staticmethod
    def active_membership_exists(company_id: str | uuid.UUID, user_id: str | uuid.UUID) -> bool:
        return CompanyMembership.objects.filter(
            company_id=company_id, user_id=user_id
        ).exists()

    @staticmethod
    def lock_active_role_membership_ids(
        company_id: str | uuid.UUID, role_id: str | uuid.UUID
    ) -> list:
        """
        BE-069 last-owner invariant, concurrency safety (Phase 8): locks
        (`SELECT ... FOR UPDATE`) every currently-active membership row
        holding `role_id` in this company, for the remaining lifetime of
        the caller's `transaction.atomic()` block -- must only be called
        from inside one. A second concurrent transaction attempting to
        mutate any of these same rows blocks until the first commits or
        rolls back, then re-evaluates the now-current set -- this is what
        makes "reject if this would remove the company's last active
        Owner" correct even when two requests race to demote/remove two
        different Owners at once.

        Returns a plain list of ids (never `.count()`) — PostgreSQL
        rejects `SELECT ... FOR UPDATE` combined with an aggregate;
        callers use `len(...)`.
        """
        return list(
            CompanyMembership.objects.select_for_update()
            .filter(
                company_id=company_id,
                role_id=role_id,
                status=CompanyMembershipStatus.ACTIVE,
                deleted_at__isnull=True,
            )
            .values_list("id", flat=True)
        )

    @staticmethod
    def create(**fields: Any) -> CompanyMembership:
        return CompanyMembership.objects.create(**fields)

    @staticmethod
    def save(membership: CompanyMembership, fields: Optional[Dict[str, Any]] = None) -> CompanyMembership:
        for field, value in (fields or {}).items():
            setattr(membership, field, value)
        membership.save()
        return membership

    @staticmethod
    def soft_delete(membership: CompanyMembership) -> None:
        membership.delete()

    @staticmethod
    def get_user_by_email(email: str) -> User:
        try:
            return User.objects.get(email__iexact=email.strip())
        except User.DoesNotExist:
            raise drf_exceptions.NotFound("No user exists with this email address.")

    @staticmethod
    def get_user_by_email_or_none(email: str) -> Optional[User]:
        """
        Non-raising counterpart to get_user_by_email, for callers (Add User)
        that need to distinguish "create a new account" from "link the
        existing one" rather than treating a miss as an error.
        """
        return User.objects.filter(email__iexact=email.strip()).first()

    @staticmethod
    def get_membership_including_revoked(
        company_id: str | uuid.UUID, user_id: str | uuid.UUID
    ) -> Optional[CompanyMembership]:
        """
        Unlike active_membership_exists (a bool used by the invite flow),
        this returns the row itself — Add User needs to tell a revoked
        membership (safe to reactivate) apart from an active/invited one
        (a genuine 409), not just know that *some* row exists.
        """
        return CompanyMembershipRepository.all().filter(company_id=company_id, user_id=user_id).first()

    @staticmethod
    def get_role_by_id(role_id: str | uuid.UUID) -> Role:
        try:
            return Role.objects.get(id=role_id)
        except (Role.DoesNotExist, ValueError):
            raise drf_exceptions.NotFound("The specified role was not found.")
