from django.contrib import admin

from apps.products.models import ProductCategory


@admin.register(ProductCategory)
class ProductCategoryAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "company",
        "created_at",
        "is_deleted",
    )
    list_filter = (
        "company",
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

    def is_deleted(self, obj: ProductCategory) -> bool:
        return obj.is_deleted

    is_deleted.boolean = True
    is_deleted.short_description = "Deleted"

    def get_queryset(self, request):
        return ProductCategory.all_objects.all()
