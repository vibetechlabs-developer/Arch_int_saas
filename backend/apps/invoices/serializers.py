from decimal import Decimal

from rest_framework import serializers

from apps.invoices.models import Invoice, InvoiceItem
from apps.invoices.selectors import VALID_INVOICE_ORDER_FIELDS
from apps.invoices.services import InvoiceService
from apps.products.models import ProductUnit


class InvoiceItemSerializer(serializers.ModelSerializer):
    """
    Output serializer for an InvoiceItem, nested under InvoiceSerializer.
    No independent input/create serializer -- items are only ever written
    as part of InvoiceCreateSerializer/InvoiceUpdateSerializer's `items`
    list.
    """

    class Meta:
        model = InvoiceItem
        fields = ["id", "description", "quantity", "unit", "rate", "amount"]
        read_only_fields = fields


class InvoiceSerializer(serializers.ModelSerializer):
    """
    Output serializer for Invoice, with camelCase JSON fields matching
    every other serializer in this codebase. `status` is a
    SerializerMethodField, not the raw model field -- it reports
    InvoiceService.compute_effective_status's read-time-derived value
    (showing `overdue` when applicable), not the persisted column
    verbatim.
    """

    companyId = serializers.UUIDField(source="company_id", read_only=True)
    projectId = serializers.UUIDField(source="project_id", read_only=True)
    projectName = serializers.CharField(source="project.name", read_only=True)
    quotationId = serializers.UUIDField(source="quotation_id", read_only=True, allow_null=True)
    clientId = serializers.UUIDField(source="client_id", read_only=True)
    clientName = serializers.CharField(source="client.name", read_only=True)
    invoiceNumber = serializers.CharField(source="invoice_number", read_only=True)
    subtotal = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)
    discount = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)
    tax = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)
    total = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)
    dueDate = serializers.DateField(source="due_date", read_only=True, allow_null=True)
    paymentTerms = serializers.CharField(source="payment_terms", read_only=True)
    status = serializers.SerializerMethodField()
    # BE-074: backend-authoritative payment aggregates -- read-only by
    # construction (SerializerMethodField has no setter, and neither field
    # is listed in InvoiceUpdateSerializer, so a client-supplied
    # paidAmount/outstandingAmount in a PATCH body is simply ignored, never
    # applied). Never reconstructed on the frontend from PaymentHistory.
    paidAmount = serializers.SerializerMethodField()
    outstandingAmount = serializers.SerializerMethodField()
    items = InvoiceItemSerializer(many=True, read_only=True)
    createdAt = serializers.DateTimeField(source="created_at", read_only=True)
    updatedAt = serializers.DateTimeField(source="updated_at", read_only=True)

    class Meta:
        model = Invoice
        fields = [
            "id",
            "companyId",
            "projectId",
            "projectName",
            "quotationId",
            "clientId",
            "clientName",
            "invoiceNumber",
            "subtotal",
            "discount",
            "tax",
            "total",
            "dueDate",
            "paymentTerms",
            "status",
            "paidAmount",
            "outstandingAmount",
            "notes",
            "items",
            "createdAt",
            "updatedAt",
        ]
        read_only_fields = fields

    def get_status(self, obj: Invoice) -> str:
        return InvoiceService.compute_effective_status(obj)

    def get_paidAmount(self, obj: Invoice) -> str:
        return str(InvoiceService.get_paid_amount(obj))

    def get_outstandingAmount(self, obj: Invoice) -> str:
        return str(InvoiceService.compute_outstanding_amount(obj))


class InvoiceItemInputSerializer(serializers.Serializer):
    """
    Input shape for one item within InvoiceCreateSerializer/
    InvoiceUpdateSerializer's `items` list. No `productId` -- InvoiceItem
    has no product FK (Database_Schema.md's literal column list).
    """

    description = serializers.CharField(required=True, allow_blank=False)
    quantity = serializers.DecimalField(
        max_digits=12, decimal_places=2, required=True, min_value=Decimal("0.01")
    )
    unit = serializers.ChoiceField(choices=ProductUnit.choices, required=False, allow_blank=True, default="")
    rate = serializers.DecimalField(max_digits=14, decimal_places=2, required=True)


class InvoiceCreateSerializer(serializers.Serializer):
    """
    Input serializer for `POST /projects/{projectId}/invoices` (BE-042).
    Exactly one of `quotationId`/`items` must be supplied -- enforced in
    InvoiceService.create_invoice, not here, since it's a cross-field rule
    best expressed as a single clear error rather than two independent
    field validators.
    """

    quotationId = serializers.UUIDField(source="quotation_id", required=False, allow_null=True, default=None)
    items = InvoiceItemInputSerializer(many=True, required=False)
    discount = serializers.DecimalField(
        max_digits=14, decimal_places=2, required=False, allow_null=True, default=None
    )
    tax = serializers.DecimalField(
        max_digits=14, decimal_places=2, required=False, allow_null=True, default=None
    )
    dueDate = serializers.DateField(source="due_date", required=False, allow_null=True, default=None)
    paymentTerms = serializers.CharField(
        source="payment_terms", required=False, allow_blank=True, default=""
    )
    notes = serializers.CharField(required=False, allow_blank=True, default="")


class InvoiceUpdateSerializer(serializers.Serializer):
    """
    Input serializer for `PATCH /invoices/{invoiceId}` (BE-042, "Edit
    (draft only)"). Every field is optional with no non-None default --
    an omitted field's absence signals InvoiceService.update_invoice to
    leave it unchanged, the same contract
    apps.quotations.serializers.QuotationReviseSerializer established.
    """

    items = InvoiceItemInputSerializer(many=True, required=False)
    discount = serializers.DecimalField(
        max_digits=14, decimal_places=2, required=False, allow_null=True, default=None
    )
    tax = serializers.DecimalField(
        max_digits=14, decimal_places=2, required=False, allow_null=True, default=None
    )
    dueDate = serializers.DateField(source="due_date", required=False, allow_null=True, default=None)
    paymentTerms = serializers.CharField(
        source="payment_terms", required=False, allow_blank=True, default=None, allow_null=True
    )
    notes = serializers.CharField(required=False, allow_blank=True, default=None, allow_null=True)


class InvoiceListQuerySerializer(serializers.Serializer):
    """
    Validates ?ordering= query params for GET /projects/{projectId}/invoices.
    """

    ordering = serializers.ChoiceField(
        choices=sorted(VALID_INVOICE_ORDER_FIELDS), required=False, default="-created_at"
    )
