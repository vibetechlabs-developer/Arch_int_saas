from django.contrib import admin

from apps.invoices.models import Invoice, InvoiceItem


class InvoiceItemInline(admin.TabularInline):
    model = InvoiceItem
    extra = 0
    readonly_fields = ("id", "created_at", "updated_at")


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = (
        "invoice_number",
        "project",
        "company",
        "status",
        "total",
        "due_date",
        "created_at",
        "is_deleted",
    )
    list_filter = (
        "company",
        "status",
        "deleted_at",
    )
    search_fields = (
        "invoice_number",
    )
    readonly_fields = (
        "id",
        "created_at",
        "updated_at",
        "deleted_at",
    )
    inlines = [InvoiceItemInline]

    def is_deleted(self, obj: Invoice) -> bool:
        return obj.is_deleted

    is_deleted.boolean = True
    is_deleted.short_description = "Deleted"

    def get_queryset(self, request):
        return Invoice.all_objects.all()
