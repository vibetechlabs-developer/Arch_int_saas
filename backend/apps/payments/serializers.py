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
            "notes",
            "createdAt",
            "updatedAt",
        ]
        read_only_fields = fields


class PaymentCreateSerializer(serializers.Serializer):
    """
    Input serializer for `POST /invoices/{invoiceId}/payments` (BE-043).
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
    notes = serializers.CharField(required=False, allow_blank=True, default="")
