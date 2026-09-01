from decimal import Decimal

from rest_framework import serializers

from apps.products.models import ProductUnit
from apps.quotations.models import Quotation, QuotationItem, QuotationStatus
from apps.quotations.selectors import VALID_QUOTATION_ORDER_FIELDS


class QuotationItemSerializer(serializers.ModelSerializer):
    """
    Output serializer for a QuotationItem, nested under QuotationSerializer.
    No independent input/create serializer exists for this model -- items
    are only ever written as part of QuotationCreateSerializer/
    QuotationReviseSerializer's `items` list.
    """

    productId = serializers.UUIDField(source="product_id", read_only=True, allow_null=True)
    productName = serializers.CharField(
        source="product.name", read_only=True, allow_null=True, default=None
    )

    class Meta:
        model = QuotationItem
        fields = ["id", "productId", "productName", "description", "quantity", "unit", "rate", "amount"]
        read_only_fields = fields


class QuotationSerializer(serializers.ModelSerializer):
    """
    Output serializer for Quotation, with camelCase JSON fields matching
    every other serializer in this codebase. `items` is always nested
    (mirrors BOQSectionSerializer nesting its own items) -- Finance_API.md
    never documents a separate items-list endpoint.
    """

    companyId = serializers.UUIDField(source="company_id", read_only=True)
    projectId = serializers.UUIDField(source="project_id", read_only=True)
    projectName = serializers.CharField(source="project.name", read_only=True)
    boqId = serializers.UUIDField(source="boq_id", read_only=True, allow_null=True)
    clientId = serializers.UUIDField(source="client_id", read_only=True)
    clientName = serializers.CharField(source="client.name", read_only=True)
    quoteNumber = serializers.CharField(source="quote_number", read_only=True)
    subtotal = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)
    discount = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)
    tax = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)
    total = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)
    paymentSchedule = serializers.JSONField(source="payment_schedule", read_only=True)
    validUntil = serializers.DateField(source="valid_until", read_only=True, allow_null=True)
    items = QuotationItemSerializer(many=True, read_only=True)
    createdAt = serializers.DateTimeField(source="created_at", read_only=True)
    updatedAt = serializers.DateTimeField(source="updated_at", read_only=True)

    class Meta:
        model = Quotation
        fields = [
            "id",
            "companyId",
            "projectId",
            "projectName",
            "boqId",
            "clientId",
            "clientName",
            "quoteNumber",
            "version",
            "subtotal",
            "discount",
            "tax",
            "total",
            "terms",
            "paymentSchedule",
            "validUntil",
            "status",
            "notes",
            "items",
            "createdAt",
            "updatedAt",
        ]
        read_only_fields = fields


class QuotationItemInputSerializer(serializers.Serializer):
    """
    Input shape for one item within QuotationCreateSerializer/
    QuotationReviseSerializer's `items` list. Mirrors
    apps.boq.serializers.BOQItemCreateSerializer's product-or-free-text
    shape, minus discount/tax (QuotationItem has no such column).
    """

    productId = serializers.UUIDField(source="product_id", required=False, allow_null=True, default=None)
    description = serializers.CharField(required=False, allow_blank=True, default="")
    quantity = serializers.DecimalField(
        max_digits=12, decimal_places=2, required=True, min_value=Decimal("0.01")
    )
    unit = serializers.ChoiceField(choices=ProductUnit.choices, required=False, allow_blank=True, default="")
    rate = serializers.DecimalField(
        max_digits=14, decimal_places=2, required=False, allow_null=True, default=None
    )


class QuotationCreateSerializer(serializers.Serializer):
    """
    Input serializer for `POST /projects/{projectId}/quotations` (BE-039).
    `items` is deliberately `required=False` with no `default` -- its
    *absence* from the request body (not an empty list) is the signal
    QuotationService.create_quotation uses to pull items from the
    project's BOQ instead (Finance_API.md: "Create quotation (optionally
    from BOQ)").
    """

    items = QuotationItemInputSerializer(many=True, required=False)
    discount = serializers.DecimalField(
        max_digits=14, decimal_places=2, required=False, allow_null=True, default=None
    )
    tax = serializers.DecimalField(
        max_digits=14, decimal_places=2, required=False, allow_null=True, default=None
    )
    terms = serializers.CharField(required=False, allow_blank=True, default="")
    paymentSchedule = serializers.JSONField(source="payment_schedule", required=False, default=list)
    validUntil = serializers.DateField(source="valid_until", required=False, allow_null=True, default=None)
    notes = serializers.CharField(required=False, allow_blank=True, default="")


class QuotationReviseSerializer(serializers.Serializer):
    """
    Input serializer for `POST /quotations/{quotationId}/revise` (BE-040).
    Every field is optional and, unlike QuotationCreateSerializer, has no
    non-None default -- an omitted field's absence from validated_data
    signals QuotationService.revise_quotation to carry the source
    version's own value forward unchanged, rather than resetting it.
    """

    items = QuotationItemInputSerializer(many=True, required=False)
    discount = serializers.DecimalField(
        max_digits=14, decimal_places=2, required=False, allow_null=True, default=None
    )
    tax = serializers.DecimalField(
        max_digits=14, decimal_places=2, required=False, allow_null=True, default=None
    )
    terms = serializers.CharField(required=False, allow_blank=True, default=None, allow_null=True)
    paymentSchedule = serializers.JSONField(
        source="payment_schedule", required=False, default=None, allow_null=True
    )
    validUntil = serializers.DateField(source="valid_until", required=False, allow_null=True, default=None)
    notes = serializers.CharField(required=False, allow_blank=True, default=None, allow_null=True)


class QuotationListQuerySerializer(serializers.Serializer):
    """
    Validates ?ordering= query params for
    GET /projects/{projectId}/quotations. No status/version filter --
    Finance_API.md documents this endpoint as returning "all versions",
    with no query params of its own.
    """

    ordering = serializers.ChoiceField(
        choices=sorted(VALID_QUOTATION_ORDER_FIELDS), required=False, default="-created_at"
    )
