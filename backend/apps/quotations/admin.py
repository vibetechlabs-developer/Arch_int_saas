from django.contrib import admin

from apps.quotations.models import Quotation, QuotationItem


class QuotationItemInline(admin.TabularInline):
    model = QuotationItem
    extra = 0
    readonly_fields = ("id", "created_at", "updated_at")


@admin.register(Quotation)
class QuotationAdmin(admin.ModelAdmin):
    list_display = (
        "quote_number",
        "version",
        "project",
        "company",
        "status",
        "total",
        "created_at",
        "is_deleted",
    )
    list_filter = (
        "company",
        "status",
        "deleted_at",
    )
    search_fields = (
        "quote_number",
    )
    readonly_fields = (
        "id",
        "created_at",
        "updated_at",
        "deleted_at",
    )
    inlines = [QuotationItemInline]

    def is_deleted(self, obj: Quotation) -> bool:
        return obj.is_deleted

    is_deleted.boolean = True
    is_deleted.short_description = "Deleted"

    def get_queryset(self, request):
        return Quotation.all_objects.all()
