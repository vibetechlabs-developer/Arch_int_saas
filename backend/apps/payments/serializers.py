from rest_framework import serializers

from apps.payments.models import Payment


class PaymentSerializer(serializers.ModelSerializer):
    """
    Output serializer for Payment, with camelCase JSON fields matching
    every other serializer in this codebase.
    """

    companyId = serializers.UUIDField(source="company_id", read_only=True)
    invoiceId = serializers.UUIDField(source="invoice_id", read_only=True)
    clientId = serializers.UUIDField(source="client_id", read_only=True)
    projectId = serializers.UUIDField(source="project_id", read_only=True)
    paymentDate = serializers.DateField(source="payment_date", read_only=True)
    amount = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)
    referenceNumber = serializers.CharField(source="reference_number", read_only=True)
    receiptUrl = serializers.URLField(source="receipt_url", read_only=True)
    hasStoredReceipt = serializers.SerializerMethodField(
        help_text="True when this receipt was uploaded via POST /payments/receipts/upload -- fetch it through GET /payments/{id}/receipt rather than receiptUrl (blank in that case)."
    )
    createdAt = serializers.DateTimeField(source="created_at", read_only=True)
    updatedAt = serializers.DateTimeField(source="updated_at", read_only=True)

    class Meta:
        model = Payment
        fields = [
            "id",
            "companyId",
            "invoiceId",
            "clientId",
            "projectId",
            "paymentDate",
            "amount",
            "method",
            "referenceNumber",
            "receiptUrl",
            "hasStoredReceipt",
            "notes",
            "createdAt",
            "updatedAt",
        ]
        read_only_fields = fields

    def get_hasStoredReceipt(self, obj: Payment) -> bool:
        return bool(obj.receipt_storage_key)


class PaymentCreateSerializer(serializers.Serializer):
    """
    Input serializer for `POST /invoices/{invoiceId}/payments` (BE-043).
    `receiptStorageKey` (BE-078) is the `key` returned by
    `POST /payments/receipts/upload` -- provide it alongside a blank
    `receiptUrl`, or provide `receiptUrl` alone for a legacy manual entry;
    never both. Payment has no update endpoint (create + void only), so
    a receipt is only ever attached here, at creation.
    """

    paymentDate = serializers.DateField(source="payment_date", required=True)
    amount = serializers.DecimalField(max_digits=14, decimal_places=2, required=True)
    method = serializers.CharField(required=False, allow_blank=True, default="")
    referenceNumber = serializers.CharField(
        source="reference_number", required=False, allow_blank=True, default=""
    )
    receiptUrl = serializers.URLField(
        source="receipt_url", required=False, allow_blank=True, default="", max_length=500
    )
    receiptStorageKey = serializers.CharField(
        source="receipt_storage_key",
        required=False,
        allow_blank=True,
        default="",
        max_length=500,
        write_only=True,
        help_text="The `key` returned by POST /payments/receipts/upload. Provide this or receiptUrl, not both.",
    )
    notes = serializers.CharField(required=False, allow_blank=True, default="")

    def validate(self, attrs):
        receipt_url = attrs.get("receipt_url", "")
        receipt_key = attrs.get("receipt_storage_key", "")
        if receipt_url and receipt_key:
            raise serializers.ValidationError(
                {"receiptUrl": ["Provide either receiptUrl or receiptStorageKey, not both."]}
            )
        return attrs


class PaymentReceiptUploadSerializer(serializers.Serializer):
    """
    Output shape for `POST /payments/receipts/upload` (BE-078, PRIVATE
    scope). Mirrors `apps.documents.serializers.DocumentUploadSerializer`
    exactly.
    """

    key = serializers.CharField()
    fileName = serializers.CharField()
    contentType = serializers.CharField()
    size = serializers.IntegerField()
