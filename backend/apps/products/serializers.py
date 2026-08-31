from rest_framework import serializers

from apps.products.models import Product, ProductCategory, ProductStatus, ProductSubcategory, ProductUnit
from apps.products.selectors import (
    VALID_CATEGORY_ORDER_FIELDS,
    VALID_PRODUCT_ORDER_FIELDS,
    VALID_SUBCATEGORY_ORDER_FIELDS,
)


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


class ProductSerializer(serializers.ModelSerializer):
    """
    Serializer for Product with camelCase JSON fields, matching
    ProjectSerializer's `clientName`-style read-only display convenience
    pattern for `subcategoryName`/`categoryName`.
    """

    companyId = serializers.UUIDField(source="company_id", read_only=True)
    subcategoryId = serializers.UUIDField(source="subcategory_id", read_only=True)
    subcategoryName = serializers.CharField(source="subcategory.name", read_only=True)
    categoryId = serializers.UUIDField(source="subcategory.category_id", read_only=True)
    categoryName = serializers.CharField(source="subcategory.category.name", read_only=True)
    imageUrl = serializers.URLField(
        source="image_url", required=False, allow_blank=True, max_length=500
    )
    defaultCost = serializers.DecimalField(
        source="default_cost", max_digits=14, decimal_places=2, required=False, allow_null=True
    )
    defaultSellingRate = serializers.DecimalField(
        source="default_selling_rate",
        max_digits=14,
        decimal_places=2,
        required=False,
        allow_null=True,
    )
    taxRate = serializers.DecimalField(
        source="tax_rate", max_digits=5, decimal_places=2, required=False, allow_null=True
    )
    createdAt = serializers.DateTimeField(source="created_at", read_only=True)
    updatedAt = serializers.DateTimeField(source="updated_at", read_only=True)

    class Meta:
        model = Product
        fields = [
            "id",
            "name",
            "companyId",
            "subcategoryId",
            "subcategoryName",
            "categoryId",
            "categoryName",
            "imageUrl",
            "unit",
            "defaultCost",
            "defaultSellingRate",
            "taxRate",
            "status",
            "createdAt",
            "updatedAt",
        ]
        read_only_fields = [
            "id",
            "companyId",
            "subcategoryId",
            "subcategoryName",
            "categoryId",
            "categoryName",
            "createdAt",
            "updatedAt",
        ]


class ProductCreateSerializer(serializers.Serializer):
    """
    Input serializer for creating a new Product. `status` is included per
    BOQ_API.md's own text ("Create product/work item (unit, default cost,
    default rate, tax, status)") — unlike Project, where status is
    deliberately excluded from create.
    """

    name = serializers.CharField(max_length=255, required=True)
    subcategoryId = serializers.UUIDField(source="subcategory_id", required=True)
    imageUrl = serializers.URLField(
        source="image_url", required=False, allow_blank=True, default="", max_length=500
    )
    unit = serializers.ChoiceField(
        choices=ProductUnit.choices, required=False, allow_blank=True, default=""
    )
    defaultCost = serializers.DecimalField(
        source="default_cost",
        max_digits=14,
        decimal_places=2,
        required=False,
        allow_null=True,
        default=None,
    )
    defaultSellingRate = serializers.DecimalField(
        source="default_selling_rate",
        max_digits=14,
        decimal_places=2,
        required=False,
        allow_null=True,
        default=None,
    )
    taxRate = serializers.DecimalField(
        source="tax_rate",
        max_digits=5,
        decimal_places=2,
        required=False,
        allow_null=True,
        default=None,
    )
    status = serializers.ChoiceField(
        choices=ProductStatus.choices, required=False, default=ProductStatus.ACTIVE
    )
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
            raise serializers.ValidationError("Product name cannot be blank or empty.")
        return cleaned


class ProductUpdateSerializer(serializers.Serializer):
    """
    Input serializer for updating an existing Product. No `subcategory`
    field — reassignment is not documented as supported, mirroring
    ProjectUpdateSerializer's exclusion of `client`.
    """

    name = serializers.CharField(max_length=255, required=False)
    imageUrl = serializers.URLField(
        source="image_url", required=False, allow_blank=True, max_length=500
    )
    unit = serializers.ChoiceField(choices=ProductUnit.choices, required=False, allow_blank=True)
    defaultCost = serializers.DecimalField(
        source="default_cost", max_digits=14, decimal_places=2, required=False, allow_null=True
    )
    defaultSellingRate = serializers.DecimalField(
        source="default_selling_rate",
        max_digits=14,
        decimal_places=2,
        required=False,
        allow_null=True,
    )
    taxRate = serializers.DecimalField(
        source="tax_rate", max_digits=5, decimal_places=2, required=False, allow_null=True
    )
    status = serializers.ChoiceField(choices=ProductStatus.choices, required=False)

    def validate_name(self, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise serializers.ValidationError("Product name cannot be blank or empty.")
        return cleaned


class ProductListQuerySerializer(serializers.Serializer):
    """
    Validates ?ordering= query params for GET /products. Category/
    subcategory/status filters are BE-034's task.
    """

    ordering = serializers.ChoiceField(
        choices=sorted(VALID_PRODUCT_ORDER_FIELDS), required=False, default="-created_at"
    )
