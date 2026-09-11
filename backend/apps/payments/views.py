from drf_spectacular.utils import extend_schema
from rest_framework import exceptions as drf_exceptions
from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common import storage as storage_service
from apps.common.responses import ApiResponse
from apps.common.views import ObjectPermission404Mixin
from apps.invoices.services import InvoiceService
from apps.payments.serializers import (
    PaymentCreateSerializer,
    PaymentReceiptUploadSerializer,
    PaymentSerializer,
)
from apps.payments.services import PaymentReceiptUploadService, PaymentService
from apps.projects.permissions import ProjectPermission
from apps.users.permissions import is_platform_admin


class PaymentListCreateView(ObjectPermission404Mixin, APIView):
    """
    `GET`/`POST /invoices/{invoiceId}/payments` (BE-043). Reuses
    ProjectPermission directly against the parent Invoice (which has its
    own real `company` column, like Quotation/Invoice) -- the same
    reasoning every nested-under-parent resource in this codebase uses.
    """

    permission_classes = [IsAuthenticated, ProjectPermission]
    permission_code_map = {"get": "payment.view", "post": "payment.create"}

    @extend_schema(
        summary="List Invoice Payments",
        description="List every payment recorded against an invoice.",
        responses={status.HTTP_200_OK: PaymentSerializer(many=True)},
        tags=["Payments"],
    )
    def get(self, request: Request, invoice_id: str = None) -> Response:
        invoice = InvoiceService.get_invoice_by_id(invoice_id)
        self.check_object_permissions(request, invoice)

        payments = PaymentService.list_payments_for_invoice(invoice)
        serializer = PaymentSerializer(payments, many=True)
        return ApiResponse.success(
            data=serializer.data, request_id=getattr(request, "request_id", None)
        )

    @extend_schema(
        summary="Record Payment",
        description="Record a payment against an invoice (date, amount, method, reference, receipt).",
        request=PaymentCreateSerializer,
        responses={status.HTTP_201_CREATED: PaymentSerializer},
        tags=["Payments"],
    )
    def post(self, request: Request, invoice_id: str = None) -> Response:
        invoice = InvoiceService.get_invoice_by_id(invoice_id)
        self.check_object_permissions(request, invoice)

        serializer = PaymentCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated = serializer.validated_data

        payment = PaymentService.create_payment(
            invoice=invoice,
            payment_date=validated["payment_date"],
            amount=validated["amount"],
            method=validated.get("method", ""),
            reference_number=validated.get("reference_number", ""),
            receipt_url=validated.get("receipt_url", ""),
            receipt_storage_key=validated.get("receipt_storage_key", ""),
            notes=validated.get("notes", ""),
            actor_user=request.user,
            request=request,
        )

        response_data = PaymentSerializer(payment).data
        return ApiResponse.created(
            data=response_data, request_id=getattr(request, "request_id", None)
        )


class PaymentReceiptUploadView(APIView):
    """
    `POST /payments/receipts/upload` (BE-078). Decoupled from any specific
    Payment row -- a receipt is always uploaded *before* the Payment it
    belongs to exists (Payment has no update endpoint to attach one
    afterward). Gated by `payment.create`, the same code
    `POST /invoices/{invoiceId}/payments` already requires.
    """

    permission_classes = [IsAuthenticated, ProjectPermission]
    parser_classes = [MultiPartParser, FormParser]
    permission_code = "payment.create"

    @extend_schema(
        summary="Upload Payment Receipt",
        description="Upload a PDF/JPEG/PNG/WEBP receipt (multipart/form-data, field name `file`, max 20 MB) to private storage. Returns a storage key usable as receiptStorageKey.",
        request={"multipart/form-data": {"type": "object", "properties": {"file": {"type": "string", "format": "binary"}}}},
        responses={status.HTTP_201_CREATED: PaymentReceiptUploadSerializer},
        tags=["Payments"],
    )
    def post(self, request: Request) -> Response:
        if is_platform_admin(request):
            company_id = request.query_params.get("companyId")
            if not company_id:
                raise drf_exceptions.ValidationError(
                    {"companyId": ["companyId is required for platform admin receipt upload."]}
                )
        else:
            company_id = request.company_id

        uploaded_file = request.FILES.get("file")
        result = PaymentReceiptUploadService.upload_receipt(
            company_id=company_id, uploaded_file=uploaded_file
        )

        response_data = PaymentReceiptUploadSerializer(result).data
        return ApiResponse.created(
            data=response_data, request_id=getattr(request, "request_id", None)
        )


class PaymentReceiptDownloadView(ObjectPermission404Mixin, APIView):
    """
    `GET /payments/{paymentId}/receipt` (BE-078) -- the only access path
    for a receipt uploaded via `POST /payments/receipts/upload`. Reuses
    `payment.view`, the same code `PaymentListCreateView.get` already
    requires.
    """

    permission_classes = [IsAuthenticated, ProjectPermission]
    permission_code_map = {"get": "payment.view"}

    @extend_schema(
        summary="Download Payment Receipt",
        responses={status.HTTP_200_OK: None},
        tags=["Payments"],
    )
    def get(self, request: Request, payment_id: str = None) -> Response:
        payment = PaymentService.get_payment_by_id(payment_id)
        self.check_object_permissions(request, payment)

        if not payment.receipt_storage_key:
            raise drf_exceptions.NotFound("This payment has no stored receipt to download.")

        key = payment.receipt_storage_key
        extension = key.rsplit(".", 1)[-1] if "." in key else "bin"
        filename = f"payment-receipt-{payment.id}.{extension}"
        return storage_service.private_file_response("payments", key, filename)


class PaymentVoidView(ObjectPermission404Mixin, APIView):
    """
    `DELETE /payments/{paymentId}` (BE-043): "Void a payment (audit-
    logged, not hard-deleted)" -- Payment has its own real `company`
    column, so ProjectPermission's generic `obj.company_id` check applies
    directly.
    """

    permission_classes = [IsAuthenticated, ProjectPermission]
    permission_code = "payment.delete"

    @extend_schema(
        summary="Void Payment",
        description="Void (soft-delete) a payment. The parent invoice's status is recomputed from its remaining payments.",
        responses={status.HTTP_200_OK: None},
        tags=["Payments"],
    )
    def delete(self, request: Request, payment_id: str = None) -> Response:
        payment = PaymentService.get_payment_by_id(payment_id)
        self.check_object_permissions(request, payment)

        PaymentService.void_payment(payment, actor_user=request.user, request=request)
        return ApiResponse.success(
            data={"message": "Payment voided successfully."},
            request_id=getattr(request, "request_id", None),
        )
