from rest_framework import serializers

from apps.boq.models import BOQ, BOQItem, BOQSection
from apps.products.models import ProductUnit


class BOQItemSerializer(serializers.ModelSerializer):
    """
    Serializer for BOQItem with camelCase JSON fields. `productName` is a
    read-only display convenience (mirrors ProjectSerializer's
    `clientName`), nullable since `product` is optional.
    """

    sectionId = serializers.UUIDField(source="boq_section_id", read_only=True)
    productId = serializers.UUIDField(source="product_id", read_only=True, allow_null=True)
    productName = serializers.CharField(
        source="product.name", read_only=True, allow_null=True, default=None
    )
    isOptional = serializers.BooleanField(source="is_optional")
    isAlternative = serializers.BooleanField(source="is_alternative")
    createdAt = serializers.DateTimeField(source="created_at", read_only=True)
    updatedAt = serializers.DateTimeField(source="updated_at", read_only=True)

    class Meta:
        model = BOQItem
        fields = [
            "id",
            "sectionId",
            "productId",
            "productName",
            "description",
            "quantity",
            "unit",
            "rate",
            "discount",
            "tax",
            "amount",
            "isOptional",
            "isAlternative",
            "notes",
            "createdAt",
            "updatedAt",
        ]
        read_only_fields = [
            "id",
            "sectionId",
            "productId",
            "productName",
            "amount",
            "createdAt",
            "updatedAt",
        ]


class BOQItemCreateSerializer(serializers.Serializer):
    """
    Input serializer for `POST .../boq/sections/{sectionId}/items`,
    matching BOQ_API.md's documented fields ("product reference or
    free-text description, quantity, unit, rate") plus discount/tax/
    optional/alternative/notes from the item schema. `description`/
    `unit`/`rate`/`tax` are optional here — BOQItemService fills them
    from the referenced product when omitted, raising ValidationError
    only if no product AND no explicit value is available. `amount` is
    never a field here — always server-computed.
    """

    productId = serializers.UUIDField(
        source="product_id", required=False, allow_null=True, default=None
    )
    description = serializers.CharField(
        max_length=500, required=False, allow_blank=True, default=""
    )
    quantity = serializers.DecimalField(max_digits=12, decimal_places=2, required=True)
    unit = serializers.ChoiceField(
        choices=ProductUnit.choices, required=False, allow_blank=True, default=""
    )
    rate = serializers.DecimalField(
        max_digits=14, decimal_places=2, required=False, allow_null=True, default=None
    )
    discount = serializers.DecimalField(
        max_digits=5, decimal_places=2, required=False, allow_null=True, default=None
    )
    tax = serializers.DecimalField(
        max_digits=5, decimal_places=2, required=False, allow_null=True, default=None
    )
    isOptional = serializers.BooleanField(source="is_optional", required=False, default=False)
    isAlternative = serializers.BooleanField(
        source="is_alternative", required=False, default=False
    )
    notes = serializers.CharField(required=False, allow_blank=True, default="")


class BOQItemUpdateSerializer(serializers.Serializer):
    """
    Input serializer for `PATCH .../boq/items/{itemId}`, matching
    BOQ_API.md exactly: "quantity/rate/discount/tax/notes/optional/
    alternative flags", plus `description`/`unit` (BE-036's own
    extension — see BOQItemService.update_item's docstring). No
    `productId`/`sectionId` — reassignment is not documented as
    supported.
    """

    description = serializers.CharField(max_length=500, required=False, allow_blank=True)
    quantity = serializers.DecimalField(max_digits=12, decimal_places=2, required=False)
    unit = serializers.ChoiceField(choices=ProductUnit.choices, required=False, allow_blank=True)
    rate = serializers.DecimalField(max_digits=14, decimal_places=2, required=False)
    discount = serializers.DecimalField(max_digits=5, decimal_places=2, required=False)
    tax = serializers.DecimalField(max_digits=5, decimal_places=2, required=False)
    isOptional = serializers.BooleanField(source="is_optional", required=False)
    isAlternative = serializers.BooleanField(source="is_alternative", required=False)
    notes = serializers.CharField(required=False, allow_blank=True)


class BOQSectionSerializer(serializers.ModelSerializer):
    """
    Serializer for BOQSection with camelCase JSON fields, including
    nested `items` (BE-036).
    """

    boqId = serializers.UUIDField(source="boq_id", read_only=True)
    sortOrder = serializers.IntegerField(source="sort_order", read_only=True)
    items = BOQItemSerializer(many=True, read_only=True)
    createdAt = serializers.DateTimeField(source="created_at", read_only=True)
    updatedAt = serializers.DateTimeField(source="updated_at", read_only=True)

    class Meta:
        model = BOQSection
        fields = ["id", "boqId", "name", "sortOrder", "items", "createdAt", "updatedAt"]
        read_only_fields = ["id", "boqId", "sortOrder", "items", "createdAt", "updatedAt"]


class BOQSectionCreateSerializer(serializers.Serializer):
    """
    Input serializer for `POST .../boq/sections`. No `sortOrder` field —
    auto-assigned server-side (append to end).
    """

    name = serializers.CharField(max_length=255, required=True)

    def validate_name(self, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise serializers.ValidationError("Section name cannot be blank or empty.")
        return cleaned


class BOQSectionUpdateSerializer(serializers.Serializer):
    """
    Input serializer for `PATCH .../boq/sections/{id}` (added for
    consistency, not documented in BOQ_API.md — see BE-031's "add missing
    CRUD" precedent).
    """

    name = serializers.CharField(max_length=255, required=False)

    def validate_name(self, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise serializers.ValidationError("Section name cannot be blank or empty.")
        return cleaned


class BOQSerializer(serializers.ModelSerializer):
    """
    Serializer for the whole BOQ tree — `GET .../boq` returns this,
    including nested sections and (from BE-036 on) each section's items.
    Read-only end to end: BOQ has no direct create/update endpoint of its
    own (see BOQService.get_or_create_boq_for_project).
    """

    projectId = serializers.UUIDField(source="project_id", read_only=True)
    sections = BOQSectionSerializer(many=True, read_only=True)
    createdAt = serializers.DateTimeField(source="created_at", read_only=True)
    updatedAt = serializers.DateTimeField(source="updated_at", read_only=True)

    class Meta:
        model = BOQ
        fields = ["id", "projectId", "status", "sections", "createdAt", "updatedAt"]
        read_only_fields = fields
