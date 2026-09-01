from django.contrib import admin

from apps.payments.models import Payment


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = (
        "invoice",
        "amount",
        "payment_date",
        "method",
        "company",
        "created_at",
        "is_deleted",
    )
    list_filter = (
        "company",
        "deleted_at",
    )
    search_fields = (
        "reference_number",
    )
    readonly_fields = (
        "id",
        "created_at",
        "updated_at",
        "deleted_at",
    )

    def is_deleted(self, obj: Payment) -> bool:
        return obj.is_deleted

    is_deleted.boolean = True
    is_deleted.short_description = "Deleted"

    def get_queryset(self, request):
        return Payment.all_objects.all()
