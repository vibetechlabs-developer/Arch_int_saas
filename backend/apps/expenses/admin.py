from django.contrib import admin

from apps.expenses.models import Expense


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = (
        "category",
        "project",
        "company",
        "amount",
        "date",
        "approval_status",
        "created_at",
        "is_deleted",
    )
    list_filter = (
        "company",
        "approval_status",
        "deleted_at",
    )
    search_fields = (
        "category",
        "vendor",
    )
    readonly_fields = (
        "id",
        "created_at",
        "updated_at",
        "deleted_at",
    )

    def is_deleted(self, obj: Expense) -> bool:
        return obj.is_deleted

    is_deleted.boolean = True
    is_deleted.short_description = "Deleted"

    def get_queryset(self, request):
        return Expense.all_objects.all()
