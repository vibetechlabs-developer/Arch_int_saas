from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from apps.users.models import CompanyMembership, Permission, Role, RolePermission, User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """
    Admin configuration for the custom User model.
    """

    list_display = (
        "email",
        "name",
        "is_active",
        "is_staff",
        "is_superuser",
        "created_at",
    )
    list_filter = ("is_active", "is_staff", "is_superuser")
    search_fields = ("email", "name")
    ordering = ("-created_at",)
    readonly_fields = ("id", "created_at", "updated_at", "deleted_at")

    fieldsets = (
        (None, {"fields": ("id", "email", "password")}),
        ("Personal info", {"fields": ("name",)}),
        (
            "Permissions",
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                ),
            },
        ),
        (
            "Important dates",
            {"fields": ("last_login", "created_at", "updated_at", "deleted_at")},
        ),
    )

    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "name", "password1", "password2"),
            },
        ),
    )


@admin.register(CompanyMembership)
class CompanyMembershipAdmin(admin.ModelAdmin):
    """
    Admin configuration for CompanyMembership.
    """

    list_display = (
        "user",
        "company",
        "role",
        "status",
        "created_at",
        "is_deleted",
    )
    list_filter = ("status", "deleted_at")
    search_fields = (
        "user__email",
        "user__name",
        "company__name",
    )
    readonly_fields = ("id", "created_at", "updated_at", "deleted_at")
    raw_id_fields = ("user", "company", "role")

    def is_deleted(self, obj: CompanyMembership) -> bool:
        return obj.is_deleted

    is_deleted.boolean = True
    is_deleted.short_description = "Deleted"

    def get_queryset(self, request):
        return CompanyMembership.all_objects.all()


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    """
    Admin configuration for Role.
    """

    list_display = (
        "name",
        "company",
        "is_active",
        "created_at",
        "is_deleted",
    )
    list_filter = ("is_active", "deleted_at")
    search_fields = (
        "name",
        "description",
        "company__name",
    )
    readonly_fields = ("id", "created_at", "updated_at", "deleted_at")
    raw_id_fields = ("company",)

    def is_deleted(self, obj: Role) -> bool:
        return obj.is_deleted

    is_deleted.boolean = True
    is_deleted.short_description = "Deleted"

    def get_queryset(self, request):
        return Role.all_objects.all()


@admin.register(Permission)
class PermissionAdmin(admin.ModelAdmin):
    """
    Admin configuration for the global Permission catalog.
    """

    list_display = ("code", "module", "action", "created_at")
    list_filter = ("module", "action")
    search_fields = ("code", "module", "description")
    readonly_fields = ("id", "created_at", "updated_at", "deleted_at")


@admin.register(RolePermission)
class RolePermissionAdmin(admin.ModelAdmin):
    """
    Admin configuration for Role <-> Permission grants.
    """

    list_display = ("role", "permission", "created_at", "is_deleted")
    list_filter = ("deleted_at",)
    search_fields = ("role__name", "permission__code")
    readonly_fields = ("id", "created_at", "updated_at", "deleted_at")
    raw_id_fields = ("role", "permission")

    def is_deleted(self, obj: RolePermission) -> bool:
        return obj.is_deleted

    is_deleted.boolean = True
    is_deleted.short_description = "Deleted"

    def get_queryset(self, request):
        return RolePermission.all_objects.all()

