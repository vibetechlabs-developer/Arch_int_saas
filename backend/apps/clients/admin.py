from django.contrib import admin

from apps.clients.models import Client


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "company_name",
        "company",
        "email",
        "mobile",
        "created_at",
        "is_deleted",
    )
    list_filter = (
        "company",
        "deleted_at",
    )
    search_fields = (
        "name",
        "company_name",
        "email",
        "mobile",
        "gstin",
    )
    readonly_fields = (
        "id",
        "created_at",
        "updated_at",
        "deleted_at",
    )

    def is_deleted(self, obj: Client) -> bool:
        return obj.is_deleted

    is_deleted.boolean = True
    is_deleted.short_description = "Deleted"

    def get_queryset(self, request):
        # Admin should display all records including soft-deleted ones
        return Client.all_objects.all()
