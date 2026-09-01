import uuid
from decimal import Decimal
from typing import Any

from django.db.models import QuerySet, Sum
from rest_framework import exceptions as drf_exceptions

from apps.payments.models import Payment


class PaymentRepository:
    """
    Data-access layer for Payment (BE-043).
    """

    @staticmethod
    def all_for_invoice(invoice_id: str | uuid.UUID) -> QuerySet[Payment]:
        return Payment.objects.select_related("company", "invoice", "client", "project").filter(
            invoice_id=invoice_id
        )

    @staticmethod
    def get_by_id(payment_id: str | uuid.UUID) -> Payment:
        try:
            return Payment.objects.select_related("company", "invoice", "client", "project").get(
                id=payment_id
            )
        except (Payment.DoesNotExist, ValueError):
            raise drf_exceptions.NotFound("The requested payment was not found.")

    @staticmethod
    def create(**fields: Any) -> Payment:
        return Payment.objects.create(**fields)

    @staticmethod
    def soft_delete(payment: Payment) -> None:
        payment.delete()

    @staticmethod
    def sum_active_amount_for_invoice(invoice_id: str | uuid.UUID) -> Decimal:
        """
        Sums only active (non-voided) payments -- `Payment.objects` is the
        SoftDeleteManager, so a just-voided payment is already excluded by
        the time PaymentService.void_payment calls this to recompute the
        invoice's status.
        """
        total = Payment.objects.filter(invoice_id=invoice_id).aggregate(total=Sum("amount"))["total"]
        return total if total is not None else Decimal("0.00")
