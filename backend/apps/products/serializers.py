from rest_framework import serializers

from apps.products.models import ProductCategory, ProductSubcategory
from apps.products.selectors import VALID_CATEGORY_ORDER_FIELDS, VALID_SUBCATEGORY_ORDER_FIELDS


class ProductCategorySerializer(serializers.ModelSerializer):
    """
    Serializer for ProductCategory with camelCase JSON fields, matching
    apps.clients.serializers.ClientSerializer.
    """

    companyId = serializers.UUIDField(source="company_id", read_only=True)
    createdAt = serializers.DateTimeField(source="created_at", read_only=True)
    updatedAt = serializers.DateTimeField(source="updated_at", read_only=True)

    class Meta:
        model = ProductCategory
        fields = ["id", "name", "companyId", "createdAt", "updatedAt"]
        read_only_fields = ["id", "companyId", "createdAt", "updatedAt"]


class ProductCategoryCreateSerializer(serializers.Serializer):
    """
    Input serializer for creating a new ProductCategory.
    """

    name = serializers.CharField(max_length=255, required=True)
    companyId = serializers.UUIDField(
        source="company_id",
        required=False,
        allow_null=True,
        default=None,
        help_text="Company UUID for platform admins. Ignored/overridden for company users.",
    )

    def validate_name(self, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise serializers.ValidationError("Category name cannot be blank or empty.")
        return cleaned


class ProductCategoryUpdateSerializer(serializers.Serializer):
    """
    Input serializer for updating an existing ProductCategory.
    """

    name = serializers.CharField(max_length=255, required=False)

    def validate_name(self, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise serializers.ValidationError("Category name cannot be blank or empty.")
        return cleaned


class ProductCategoryListQuerySerializer(serializers.Serializer):
    """
    Validates ?ordering= query params for GET /product-categories.
    """

    ordering = serializers.ChoiceField(
        choices=sorted(VALID_CATEGORY_ORDER_FIELDS), required=False, default="-created_at"
    )


class ProductSubcategorySerializer(serializers.ModelSerializer):
    """
    Serializer for ProductSubcategory with camelCase JSON fields, matching
    ProductCategorySerializer. `categoryName` is a read-only display
    convenience (mirrors ProjectSerializer's `clientName`).
    """

    companyId = serializers.UUIDField(source="company_id", read_only=True)
    categoryId = serializers.UUIDField(source="category_id", read_only=True)
    categoryName = serializers.CharField(source="category.name", read_only=True)
    createdAt = serializers.DateTimeField(source="created_at", read_only=True)
    updatedAt = serializers.DateTimeField(source="updated_at", read_only=True)

    class Meta:
        model = ProductSubcategory
        fields = [
            "id",
            "name",
            "companyId",
            "categoryId",
            "categoryName",
            "createdAt",
            "updatedAt",
        ]
        read_only_fields = ["id", "companyId", "categoryId", "categoryName", "createdAt", "updatedAt"]


class ProductSubcategoryCreateSerializer(serializers.Serializer):
    """
    Input serializer for creating a new ProductSubcategory. `category` is
    not a body field — it comes from the URL path
    (`/product-categories/{categoryId}/subcategories`), matching
    BOQ_API.md's nested endpoint shape.
    """

    name = serializers.CharField(max_length=255, required=True)

    def validate_name(self, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise serializers.ValidationError("Subcategory name cannot be blank or empty.")
        return cleaned


class ProductSubcategoryUpdateSerializer(serializers.Serializer):
    """
    Input serializer for updating an existing ProductSubcategory. No
    `category` field — reassignment is not documented as supported.
    """

    name = serializers.CharField(max_length=255, required=False)

    def validate_name(self, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise serializers.ValidationError("Subcategory name cannot be blank or empty.")
        return cleaned


class ProductSubcategoryListQuerySerializer(serializers.Serializer):
    """
    Validates ?ordering= query params for
    GET /product-categories/{categoryId}/subcategories.
    """

    ordering = serializers.ChoiceField(
        choices=sorted(VALID_SUBCATEGORY_ORDER_FIELDS), required=False, default="-created_at"
    )
