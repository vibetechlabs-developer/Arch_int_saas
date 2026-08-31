from django.contrib import admin

from apps.boq.models import BOQ, BOQItem, BOQSection


@admin.register(BOQ)
class BOQAdmin(admin.ModelAdmin):
    list_display = (
        "project",
        "company",
        "status",
        "created_at",
        "is_deleted",
    )
    list_filter = (
        "company",
        "deleted_at",
    )
    readonly_fields = (
        "id",
        "created_at",
        "updated_at",
        "deleted_at",
    )

    def is_deleted(self, obj: BOQ) -> bool:
        return obj.is_deleted

    is_deleted.boolean = True
    is_deleted.short_description = "Deleted"

    def get_queryset(self, request):
        return BOQ.all_objects.all()


@admin.register(BOQSection)
class BOQSectionAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "boq",
        "sort_order",
        "created_at",
        "is_deleted",
    )
    list_filter = (
        "deleted_at",
    )
    search_fields = (
        "name",
    )
    readonly_fields = (
        "id",
        "created_at",
        "updated_at",
        "deleted_at",
    )

    def is_deleted(self, obj: BOQSection) -> bool:
        return obj.is_deleted

    is_deleted.boolean = True
    is_deleted.short_description = "Deleted"

    def get_queryset(self, request):
        return BOQSection.all_objects.all()


@admin.register(BOQItem)
class BOQItemAdmin(admin.ModelAdmin):
    list_display = (
        "description",
        "boq_section",
        "product",
        "quantity",
        "rate",
        "amount",
        "is_optional",
        "is_alternative",
        "created_at",
        "is_deleted",
    )
    list_filter = (
        "is_optional",
        "is_alternative",
        "deleted_at",
    )
    search_fields = (
        "description",
    )
    readonly_fields = (
        "id",
        "amount",
        "created_at",
        "updated_at",
        "deleted_at",
    )

    def is_deleted(self, obj: BOQItem) -> bool:
        return obj.is_deleted

    is_deleted.boolean = True
    is_deleted.short_description = "Deleted"

    def get_queryset(self, request):
        return BOQItem.all_objects.all()
