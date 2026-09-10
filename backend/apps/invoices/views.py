from django.http import HttpResponse
from django.utils import timezone
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.pdf_service import pdf_http_response, render_pdf
from apps.common.responses import ApiResponse
from apps.common.views import ObjectPermission404Mixin
from apps.invoices.serializers import (
    InvoiceCreateSerializer,
    InvoiceListQuerySerializer,
    InvoiceSerializer,
    InvoiceUpdateSerializer,
)
from apps.invoices.models import InvoiceStatus
from apps.invoices.services import InvoiceService
from apps.projects.permissions import ProjectPermission
from apps.projects.services import ProjectService


class InvoiceListCreateView(ObjectPermission404Mixin, APIView):
    """
    `GET`/`POST /projects/{projectId}/invoices` (BE-042). Reuses
    ProjectPermission directly, matching every nested-under-Project
    resource in this codebase (Invoice has its own real `company` column,
    like Quotation). Unpaginated -- same "a handful per project, not an
    unbounded tenant-wide collection" precedent as
    QuotationListCreateView.
    """

    permission_classes = [IsAuthenticated, ProjectPermission]
    permission_code_map = {"get": "invoice.view", "post": "invoice.create"}

    @extend_schema(
        summary="List Project Invoices",
        description="List every invoice for a project.",
        parameters=[
            OpenApiParameter(
                name="ordering",
                description="Ordering field (e.g. due_date, -due_date, created_at, -created_at).",
                required=False,
                type=str,
            ),
        ],
        responses={status.HTTP_200_OK: InvoiceSerializer(many=True)},
        tags=["Invoices"],
    )
    def get(self, request: Request, project_id: str = None) -> Response:
        project = ProjectService.get_project_by_id(project_id)
        self.check_object_permissions(request, project)

        query = InvoiceListQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)

        queryset = InvoiceService.list_invoices_for_project(
            project, ordering=query.validated_data["ordering"]
        )

        serializer = InvoiceSerializer(queryset, many=True)
        return ApiResponse.success(
            data=serializer.data, request_id=getattr(request, "request_id", None)
        )

    @extend_schema(
        summary="Create Invoice",
        description="Create an invoice for a project, either from an approved quotation (quotationId) or ad hoc (items).",
        request=InvoiceCreateSerializer,
        responses={status.HTTP_201_CREATED: InvoiceSerializer},
        tags=["Invoices"],
    )
    def post(self, request: Request, project_id: str = None) -> Response:
        project = ProjectService.get_project_by_id(project_id)
        self.check_object_permissions(request, project)

        serializer = InvoiceCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated = serializer.validated_data

        invoice = InvoiceService.create_invoice(
            project=project,
            quotation_id=validated.get("quotation_id"),
            items=validated.get("items"),
            discount=validated.get("discount"),
            tax=validated.get("tax"),
            due_date=validated.get("due_date"),
            payment_terms=validated.get("payment_terms", ""),
            notes=validated.get("notes", ""),
            actor_user=request.user,
            request=request,
        )

        response_data = InvoiceSerializer(invoice).data
        return ApiResponse.created(
            data=response_data, request_id=getattr(request, "request_id", None)
        )


class InvoiceDetailView(ObjectPermission404Mixin, APIView):
    """
    `GET`/`PATCH /invoices/{invoiceId}` (BE-042). PATCH is "Edit (draft
    only)" per Finance_API.md -- InvoiceService.update_invoice enforces
    the draft-only guard (409 otherwise), not this view.
    """

    permission_classes = [IsAuthenticated, ProjectPermission]
    permission_code_map = {"get": "invoice.view", "patch": "invoice.edit"}

    @extend_schema(
        summary="Get Invoice",
        description="Get one invoice's full detail, including its items.",
        responses={status.HTTP_200_OK: InvoiceSerializer},
        tags=["Invoices"],
    )
    def get(self, request: Request, invoice_id: str = None) -> Response:
        invoice = InvoiceService.get_invoice_by_id(invoice_id)
        self.check_object_permissions(request, invoice)

        response_data = InvoiceSerializer(invoice).data
        return ApiResponse.success(
            data=response_data, request_id=getattr(request, "request_id", None)
        )

    @extend_schema(
        summary="Update Invoice",
        description="Edit a draft invoice. Any field omitted from the request is left unchanged.",
        request=InvoiceUpdateSerializer,
        responses={status.HTTP_200_OK: InvoiceSerializer},
        tags=["Invoices"],
    )
    def patch(self, request: Request, invoice_id: str = None) -> Response:
        invoice = InvoiceService.get_invoice_by_id(invoice_id)
        self.check_object_permissions(request, invoice)

        serializer = InvoiceUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        validated = serializer.validated_data

        updated = InvoiceService.update_invoice(
            invoice=invoice,
            items=validated.get("items"),
            discount=validated.get("discount"),
            tax=validated.get("tax"),
            due_date=validated.get("due_date"),
            payment_terms=validated.get("payment_terms"),
            notes=validated.get("notes"),
            actor_user=request.user,
            request=request,
        )

        response_data = InvoiceSerializer(updated).data
        return ApiResponse.success(
            data=response_data, request_id=getattr(request, "request_id", None)
        )


class InvoicePdfView(ObjectPermission404Mixin, APIView):
    """
    `GET /invoices/{invoiceId}/pdf` (BE-076) — server-rendered PDF export.
    Same `ProjectPermission`/`invoice.view` authorization as
    `InvoiceDetailView`. Fetches via `InvoiceService.get_invoice_by_id`
    (the same annotated-paid-amount path the JSON API uses, BE-074) so
    `paidAmount`/`outstandingAmount` are the identical backend-authoritative
    figures the Invoice Detail page shows -- never recomputed here.
    `?mode=preview` -> inline; otherwise attachment.
    """

    permission_classes = [IsAuthenticated, ProjectPermission]
    permission_code = "invoice.view"

    @extend_schema(
        summary="Export Invoice PDF",
        description="Render this invoice as a PDF. ?mode=preview for inline viewing, otherwise a download.",
        responses={status.HTTP_200_OK: {"type": "string", "format": "binary"}},
        tags=["Invoices"],
    )
    def get(self, request: Request, invoice_id: str = None) -> HttpResponse:
        invoice = InvoiceService.get_invoice_by_id(invoice_id)
        self.check_object_permissions(request, invoice)

        # select_related('company','client','project') already applied by
        # InvoiceRepository.get_by_id; items still need their own fetch --
        # a single query regardless of item count (Phase 37: no N+1).
        items = invoice.items.order_by("created_at")

        company = invoice.company
        client = invoice.client
        project = invoice.project
        effective_status = InvoiceService.compute_effective_status(invoice)
        status_choices = dict(InvoiceStatus.choices)
        context = {
            "document_title": f"Invoice {invoice.invoice_number}",
            "document_type": "INVOICE",
            "document_number": invoice.invoice_number,
            "status_label": status_choices.get(effective_status, effective_status),
            "company": company,
            "client": client,
            "project": project,
            "currency": company.currency,
            "generated_at": timezone.localtime().strftime("%d %b %Y, %H:%M"),
            "items": [
                {
                    "description": item.description,
                    "quantity": item.quantity,
                    "unit": item.get_unit_display() if item.unit else "",
                    "rate": item.rate,
                    "amount": item.amount,
                }
                for item in items
            ],
            "invoice": {
                "subtotal": invoice.subtotal,
                "discount": invoice.discount,
                "tax": invoice.tax,
                "total": invoice.total,
                "paid_amount": InvoiceService.get_paid_amount(invoice),
                "outstanding_amount": InvoiceService.compute_outstanding_amount(invoice),
                "due_date": invoice.due_date,
                "payment_terms": invoice.payment_terms,
                "notes": invoice.notes,
            },
        }

        pdf_bytes = render_pdf("pdf/invoice.html", context)
        inline = request.query_params.get("mode") == "preview"
        return pdf_http_response(pdf_bytes, filename=f"Invoice-{invoice.invoice_number}", inline=inline)


class InvoiceSendView(ObjectPermission404Mixin, APIView):
    """`POST /invoices/{invoiceId}/send` (BE-042): draft -> sent."""

    # BE-054 §5: Backend-Lead-approved provisional mapping (send ->
    # invoice.edit) — see RBAC_Enforcement_Matrix.md.
    permission_classes = [IsAuthenticated, ProjectPermission]
    permission_code = "invoice.edit"

    @extend_schema(
        summary="Send Invoice",
        description="Mark a draft invoice as sent to the client.",
        request=None,
        responses={status.HTTP_200_OK: InvoiceSerializer},
        tags=["Invoices"],
    )
    def post(self, request: Request, invoice_id: str = None) -> Response:
        invoice = InvoiceService.get_invoice_by_id(invoice_id)
        self.check_object_permissions(request, invoice)

        updated = InvoiceService.send_invoice(invoice, actor_user=request.user, request=request)

        response_data = InvoiceSerializer(updated).data
        return ApiResponse.success(
            data=response_data, request_id=getattr(request, "request_id", None)
        )


class InvoiceCancelView(ObjectPermission404Mixin, APIView):
    """`POST /invoices/{invoiceId}/cancel` (BE-042)."""

    # BE-054 §5: Backend-Lead-approved provisional mapping (cancel ->
    # invoice.edit) — see RBAC_Enforcement_Matrix.md.
    permission_classes = [IsAuthenticated, ProjectPermission]
    permission_code = "invoice.edit"

    @extend_schema(
        summary="Cancel Invoice",
        description="Cancel an invoice (blocked once fully paid or already cancelled).",
        request=None,
        responses={status.HTTP_200_OK: InvoiceSerializer},
        tags=["Invoices"],
    )
    def post(self, request: Request, invoice_id: str = None) -> Response:
        invoice = InvoiceService.get_invoice_by_id(invoice_id)
        self.check_object_permissions(request, invoice)

        updated = InvoiceService.cancel_invoice(invoice, actor_user=request.user, request=request)

        response_data = InvoiceSerializer(updated).data
        return ApiResponse.success(
            data=response_data, request_id=getattr(request, "request_id", None)
        )
