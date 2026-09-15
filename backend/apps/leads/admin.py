from django.contrib import admin

from apps.leads.models import Lead


@admin.register(Lead)
class LeadAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "company_name",
        "company",
        "status",
        "assigned_to",
        "created_at",
        "is_deleted",
    )
    list_filter = (
        "company",
        "status",
        "deleted_at",
    )
    search_fields = (
        "name",
        "company_name",
        "email",
        "mobile",
    )
    readonly_fields = (
        "id",
        "created_at",
        "updated_at",
        "deleted_at",
        "converted_client",
        "converted_project",
    )

    def is_deleted(self, obj: Lead) -> bool:
        return obj.is_deleted

    is_deleted.boolean = True
    is_deleted.short_description = "Deleted"

    def get_queryset(self, request):
        return Lead.all_objects.all()
