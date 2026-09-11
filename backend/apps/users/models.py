from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models

from apps.common.managers import (
    SoftDeleteAllManager,
    SoftDeleteDeletedManager,
    SoftDeleteManager,
)
from apps.common.models import BaseModel
from apps.users.managers import UserManager


class User(AbstractBaseUser, PermissionsMixin, BaseModel):
    """
    Custom User model for INT Projects SaaS.
    Acts as the global identity layer across all companies/tenants.
    """

    email = models.EmailField(
        unique=True,
        max_length=255,
        db_index=True,
        help_text="User's primary email address and login identifier.",
    )
    name = models.CharField(
        max_length=255,
        help_text="User's full name.",
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Designates whether this user account is active.",
    )
    is_staff = models.BooleanField(
        default=False,
        help_text="Designates whether the user can log into the Django admin site.",
    )

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["name"]

    # Managers
    objects = UserManager()
    all_objects = SoftDeleteAllManager()
    deleted_objects = SoftDeleteDeletedManager()

    class Meta:
        db_table = "user"
        ordering = ["-created_at"]
        verbose_name = "user"
        verbose_name_plural = "users"

    def __str__(self) -> str:
        return f"{self.email} ({self.name})"

    @property
    def status(self) -> str:
        """
        User status derived from is_active and soft delete status.
        """
        if self.is_deleted:
            return "deleted"
        return "active" if self.is_active else "inactive"


class CompanyMembershipStatus(models.TextChoices):
    """
    Status choices for user memberships in a company.
    """
    ACTIVE = "active", "Active"
    INVITED = "invited", "Invited"
    REVOKED = "revoked", "Revoked"


class CompanyMembership(BaseModel):
    """
    Join model associating a global User with a tenant Company.
    Acts as the anchor for tenant scoping and future role-based permissions (RBAC).
    """

    company = models.ForeignKey(
        "company.Company",
        on_delete=models.CASCADE,
        related_name="memberships",
        db_index=True,
        help_text="The tenant company this membership belongs to.",
    )
    user = models.ForeignKey(
        "users.User",
        on_delete=models.CASCADE,
        related_name="memberships",
        db_index=True,
        help_text="The user assigned to this company membership.",
    )
    status = models.CharField(
        max_length=50,
        choices=CompanyMembershipStatus.choices,
        default=CompanyMembershipStatus.ACTIVE,
        db_index=True,
        help_text="Status of the user membership in this company.",
    )
    role = models.ForeignKey(
        "users.Role",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="memberships",
        help_text=(
            "Role assigned to this membership within the company. Null until "
            "an admin assigns one (BE-050) — a membership with no role has "
            "no permission codes and, per RBAC's fail-closed default, no "
            "access beyond bare tenant membership until BE-054 enforcement "
            "lands. Must belong to the same company as this membership "
            "(validated in apps.users.validators, not by a DB constraint, "
            "since Django has no native cross-field FK-company-match "
            "constraint)."
        ),
    )

    class Meta:
        db_table = "company_membership"
        ordering = ["-created_at"]
        verbose_name = "company membership"
        verbose_name_plural = "company memberships"
        constraints = [
            models.UniqueConstraint(
                fields=["company", "user"],
                condition=models.Q(deleted_at__isnull=True),
                name="unique_active_company_user_membership",
            )
        ]

    def __str__(self) -> str:
        return f"{self.user_id} -> {self.company_id} ({self.status})"


class Role(BaseModel):
    """
    Tenant-scoped role definition.
    Each role belongs to a Company (tenant) and defines permissions within that company.
    Soft-delete is enabled through BaseModel and the custom managers.
    """

    name = models.CharField(
        max_length=100,
        help_text="Human-readable role name, unique per company.",
    )
    description = models.TextField(
        blank=True,
        help_text="Optional free-form description of the role's purpose.",
    )
    company = models.ForeignKey(
        "company.Company",
        on_delete=models.CASCADE,
        related_name="roles",
        db_index=True,
        help_text="The tenant company this role belongs to.",
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Indicates whether the role is currently usable.",
    )
    system_key = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        default=None,
        editable=False,
        help_text=(
            "Stable machine identity for a default/system role (BE-069), "
            "e.g. 'owner'. NULL for every customer-created role, "
            "including one a customer names 'Owner' -- a role's system "
            "identity is never inferred from its display `name`, which "
            "remains freely editable. Set only by "
            "RoleService.seed_default_roles_for_company at company-"
            "creation time (or by the historical backfill migration); "
            "never accepted from any API input. See "
            "apps.users.permission_catalog.OWNER_SYSTEM_KEY for the one "
            "value with dedicated protection semantics."
        ),
    )

    # objects/all_objects/deleted_objects are inherited unchanged from
    # BaseModel/SoftDeleteModel — no override needed (unlike User, which
    # overrides objects with a UserManager for create_user()/
    # create_superuser()).

    class Meta:
        db_table = "role"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["company", "system_key"],
                condition=models.Q(system_key__isnull=False),
                name="unique_system_key_per_company",
            ),
            models.UniqueConstraint(
                fields=["company", "name"],
                condition=models.Q(deleted_at__isnull=True),
                name="unique_active_role_per_company",
            )
        ]
        verbose_name = "role"
        verbose_name_plural = "roles"

    def __str__(self) -> str:
        return f"{self.name} ({self.company.name})"


class PermissionAction(models.TextChoices):
    """
    Action vocabulary from 05_Security/Permissions.md §2. The per-module
    canonical code list itself is still an open item there (§7, item 1,
    pending client sign-off) — this action set is the documented part.
    """
    VIEW = "view", "View"
    CREATE = "create", "Create"
    EDIT = "edit", "Edit"
    DELETE = "delete", "Delete"
    APPROVE = "approve", "Approve"
    EXPORT = "export", "Export"
    MANAGE = "manage", "Manage"
    FINANCIAL_ACCESS = "financial_access", "Financial Access"


class Permission(BaseModel):
    """
    Global (not tenant-scoped) permission-code catalog: `<module>.<action>`
    per 05_Security/Permissions.md §2. Seeded via a data migration from the
    documented format + action vocabulary, scoped to modules that exist in
    this codebase today. Treated as an extensible catalog, not a final one —
    §7's open item (full canonical list pending client sign-off) is not yet
    resolved, so codes may be added/renamed/removed without a redesign; no
    view currently enforces these (see BE-054).
    """

    code = models.CharField(
        max_length=100,
        unique=True,
        db_index=True,
        help_text="`<module>.<action>` permission code, e.g. 'invoice.view'.",
    )
    module = models.CharField(max_length=50, db_index=True)
    action = models.CharField(max_length=30, choices=PermissionAction.choices)
    description = models.CharField(max_length=255, blank=True, default="")

    class Meta:
        db_table = "permission"
        ordering = ["module", "action"]
        verbose_name = "permission"
        verbose_name_plural = "permissions"

    def __str__(self) -> str:
        return self.code


class RolePermission(BaseModel):
    """
    Join model granting a Permission to a Role. A Role's effective
    permission-code set is the union of its active RolePermission rows'
    Permission.code values (apps.users.services.PermissionService).
    """

    role = models.ForeignKey(
        "users.Role",
        on_delete=models.CASCADE,
        related_name="role_permissions",
    )
    permission = models.ForeignKey(
        "users.Permission",
        on_delete=models.CASCADE,
        related_name="role_permissions",
    )

    class Meta:
        db_table = "role_permission"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["role", "permission"],
                condition=models.Q(deleted_at__isnull=True),
                name="unique_active_role_permission",
            )
        ]
        verbose_name = "role permission"
        verbose_name_plural = "role permissions"

    def __str__(self) -> str:
        return f"{self.role_id} -> {self.permission_id}"

