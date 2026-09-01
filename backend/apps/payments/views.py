from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.responses import ApiResponse
from apps.common.views import ObjectPermission404Mixin
from apps.invoices.services import InvoiceService
from apps.payments.serializers import PaymentCreateSerializer, PaymentSerializer
from apps.payments.services import PaymentService
from apps.projects.permissions import ProjectPermission


class PaymentListCreateView(ObjectPermission404Mixin, APIView):
    """
    `GET`/`POST /invoices/{invoiceId}/payments` (BE-043). Reuses
    ProjectPermission directly against the parent Invoice (which has its
    own real `company` column, like Quotation/Invoice) -- the same
    reasoning every nested-under-parent resource in this codebase uses.
    """

    permission_classes = [IsAuthenticated, ProjectPermission]

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
            notes=validated.get("notes", ""),
            actor_user=request.user,
            request=request,
        )

        response_data = PaymentSerializer(payment).data
        return ApiResponse.created(
            data=response_data, request_id=getattr(request, "request_id", None)
        )


class PaymentVoidView(ObjectPermission404Mixin, APIView):
    """
    `DELETE /payments/{paymentId}` (BE-043): "Void a payment (audit-
    logged, not hard-deleted)" -- Payment has its own real `company`
    column, so ProjectPermission's generic `obj.company_id` check applies
    directly.
    """

    permission_classes = [IsAuthenticated, ProjectPermission]

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
