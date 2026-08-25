from django.contrib import admin

from apps.company.models import Company


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "status",
        "currency",
        "gst_number",
        "created_at",
        "is_deleted",
    )
    list_filter = (
        "status",
        "currency",
        "deleted_at",
    )
    search_fields = (
        "name",
        "gst_number",
    )
    readonly_fields = (
        "id",
        "created_at",
        "updated_at",
        "deleted_at",
    )

    def is_deleted(self, obj: Company) -> bool:
        return obj.is_deleted

    is_deleted.boolean = True
    is_deleted.short_description = "Deleted"

    def get_queryset(self, request):
        # Admin should display all records including soft-deleted ones
        return Company.all_objects.all()
