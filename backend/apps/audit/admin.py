from django.contrib import admin

from apps.audit.models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    """
    Read-only: an audit trail must never be editable or deletable through
    any application surface, including Django admin.
    """

    list_display = (
        "created_at",
        "action",
        "entity_type",
        "entity_id",
        "company",
        "actor_user",
        "ip_address",
    )
    list_filter = (
        "action",
        "entity_type",
        "company",
    )
    search_fields = (
        "entity_id",
        "request_id",
        "actor_user__email",
    )
    readonly_fields = [f.name for f in AuditLog._meta.fields]

    def has_add_permission(self, request) -> bool:
        return False

    def has_change_permission(self, request, obj=None) -> bool:
        return False

    def has_delete_permission(self, request, obj=None) -> bool:
        return False
