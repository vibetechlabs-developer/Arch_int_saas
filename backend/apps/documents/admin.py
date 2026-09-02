from django.contrib import admin

from apps.documents.models import Document


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = (
        "entity_type",
        "entity_id",
        "version",
        "project",
        "company",
        "created_at",
        "is_deleted",
    )
    list_filter = (
        "company",
        "entity_type",
        "deleted_at",
    )
    readonly_fields = (
        "id",
        "created_at",
        "updated_at",
        "deleted_at",
    )

    def is_deleted(self, obj: Document) -> bool:
        return obj.is_deleted

    is_deleted.boolean = True
    is_deleted.short_description = "Deleted"

    def get_queryset(self, request):
        return Document.all_objects.all()
