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

    # objects/all_objects/deleted_objects are inherited unchanged from
    # BaseModel/SoftDeleteModel — no override needed (unlike User, which
    # overrides objects with a UserManager for create_user()/
    # create_superuser()).

    class Meta:
        db_table = "role"
        ordering = ["-created_at"]
        constraints = [
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

