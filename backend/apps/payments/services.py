import datetime
import uuid
from decimal import Decimal
from typing import Any, Dict, Optional

from django.db import transaction
from django.db.models import QuerySet
from rest_framework import exceptions as drf_exceptions

from apps.audit.models import AuditAction
from apps.audit.services import AuditLogService
from apps.common import storage as storage_service
from apps.common.exceptions import ConflictError
from apps.invoices.models import Invoice, InvoiceStatus
from apps.invoices.services import InvoiceService
from apps.payments import validators
from apps.payments.models import Payment
from apps.payments.repositories import PaymentRepository

PAYMENT_AUDITED_FIELDS = (
    "invoice_id",
    "client_id",
    "project_id",
    "payment_date",
    "amount",
    "method",
    "reference_number",
    "receipt_url",
    "receipt_storage_key",
    "notes",
)

# An invoice must have actually been sent, and must not have been
# cancelled, before it can receive a payment (Backend Lead decision,
# Sprint 6 planning -- Finance_API.md doesn't spell out a precondition,
# but "record a payment against a draft/cancelled invoice" has no
# sensible real-world meaning).
UNPAYABLE_INVOICE_STATUSES = (InvoiceStatus.DRAFT, InvoiceStatus.CANCELLED)


def _serialize_payment_audit_value(value: Any) -> Any:
    """
    Same JSONField-has-no-custom-encoder reasoning as
    apps.invoices.services._serialize_invoice_audit_value.
    """
    if isinstance(value, (datetime.date, datetime.datetime)):
        return value.isoformat()
    if isinstance(value, uuid.UUID):
        return str(value)
    if isinstance(value, Decimal):
        return str(value)
    return value


def _payment_audit_state(payment: Payment) -> Dict[str, Any]:
    return {
        field: _serialize_payment_audit_value(getattr(payment, field))
        for field in PAYMENT_AUDITED_FIELDS
    }


class PaymentService:
    """
    Business logic and orchestration service for Payment management
    (BE-043). Every method takes an already-authorized `invoice`/`payment`
    instance -- tenant authorization for the parent Invoice happens at the
    view layer, mirroring ProjectMemberService's pattern. Recording or
    voiding a payment always triggers
    InvoiceService.recompute_status_from_payments, keeping the invoice's
    persisted status (draft/sent/partially_paid/paid/cancelled) in sync
    with the sum of its active payments.
    """

    @classmethod
    def list_payments_for_invoice(cls, invoice: Invoice) -> QuerySet[Payment]:
        return PaymentRepository.all_for_invoice(invoice.id)

    @classmethod
    def get_payment_by_id(
        cls,
        payment_id: str | uuid.UUID,
        company_id: Optional[str | uuid.UUID] = None,
    ) -> Payment:
        """
        Retrieve an active, non-voided Payment by primary key UUID. Raises
        NotFound if it does not exist, is already voided, or belongs to
        another company.
        """
        payment = PaymentRepository.get_by_id(payment_id)

        if company_id is not None and str(payment.company_id) != str(company_id):
            raise drf_exceptions.NotFound("The requested payment was not found.")

        return payment

    @classmethod
    def create_payment(
        cls,
        invoice: Invoice,
        payment_date: Any,
        amount: Any,
        method: str = "",
        reference_number: str = "",
        receipt_url: str = "",
        receipt_storage_key: str = "",
        notes: str = "",
        actor_user: Any = None,
        request: Any = None,
    ) -> Payment:
        """
        Record a payment against an already-authorized Invoice. Raises
        ConflictError (409) if the invoice is draft or cancelled --
        see UNPAYABLE_INVOICE_STATUSES.
        """
        with transaction.atomic():
            if invoice.status in UNPAYABLE_INVOICE_STATUSES:
                raise ConflictError(
                    f"Cannot record a payment against an invoice with status '{invoice.status}'."
                )

            cleaned_amount = validators.require_positive_amount(amount)

            payment = PaymentRepository.create(
                company=invoice.company,
                invoice=invoice,
                client=invoice.client,
                project=invoice.project,
                payment_date=payment_date,
                amount=cleaned_amount,
                method=method or "",
                reference_number=reference_number or "",
                receipt_url=receipt_url or "",
                receipt_storage_key=receipt_storage_key or "",
                notes=notes or "",
            )

            AuditLogService.record(
                action=AuditAction.CREATE,
                entity_type="payment",
                entity_id=payment.id,
                company_id=invoice.company_id,
                actor_user=actor_user,
                after_state=_payment_audit_state(payment),
                request=request,
            )

            paid_total = PaymentRepository.sum_active_amount_for_invoice(invoice.id)
            InvoiceService.recompute_status_from_payments(
                invoice, paid_total, actor_user=actor_user, request=request
            )

            return payment

    @classmethod
    def void_payment(
        cls,
        payment: Payment,
        actor_user: Any = None,
        request: Any = None,
    ) -> None:
        """
        Void (soft-delete) a Payment -- "audit-logged, not hard-deleted"
        (Finance_API.md) -- then recomputes the parent invoice's status
        from its remaining active payments.
        """
        with transaction.atomic():
            before_state = _payment_audit_state(payment)
            payment_id = payment.id
            invoice = payment.invoice

            PaymentRepository.soft_delete(payment)

            AuditLogService.record(
                action=AuditAction.DELETE,
                entity_type="payment",
                entity_id=payment_id,
                company_id=payment.company_id,
                actor_user=actor_user,
                before_state=before_state,
                request=request,
            )

            paid_total = PaymentRepository.sum_active_amount_for_invoice(invoice.id)
            InvoiceService.recompute_status_from_payments(
                invoice, paid_total, actor_user=actor_user, request=request
            )


class PaymentReceiptUploadService:
    """
    Stores a validated receipt file via the shared storage abstraction
    (BE-078, PRIVATE scope "payments") and returns the storage `key` the
    caller passes back as `receiptStorageKey` on
    `POST /invoices/{invoiceId}/payments`. Mirrors
    `apps.documents.services.DocumentUploadService` exactly. Decoupled
    from any specific Payment row on purpose -- a receipt is always
    uploaded *before* the Payment it belongs to exists, since Payment has
    no update endpoint to attach one afterward.
    """

    @classmethod
    def upload_receipt(cls, company_id: str | uuid.UUID, uploaded_file: Any) -> Dict[str, Any]:
        extension, content_type = storage_service.validate_document_upload(uploaded_file)

        storage_key = storage_service.generate_storage_key("payments", company_id, extension)
        storage_service.save_upload("payments", storage_key, uploaded_file)

        return {
            "key": storage_key,
            "fileName": storage_service.safe_display_filename(getattr(uploaded_file, "name", "")),
            "contentType": content_type,
            "size": uploaded_file.size,
        }
