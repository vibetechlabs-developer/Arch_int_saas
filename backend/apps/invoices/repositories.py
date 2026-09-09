import uuid
from decimal import Decimal
from typing import Any, Dict, List, Optional

from django.db.models import DecimalField, OuterRef, QuerySet, Subquery, Sum
from django.db.models.functions import Coalesce
from rest_framework import exceptions as drf_exceptions

from apps.company.models import Company
from apps.invoices.models import Invoice, InvoiceItem
from apps.payments.models import Payment


def with_paid_amount(queryset: QuerySet[Invoice]) -> QuerySet[Invoice]:
    """
    Annotates each Invoice in `queryset` with `paid_amount` -- the sum of
    its active (non-voided) payments -- via a correlated Subquery rather
    than a JOIN+GROUP BY (BE-074). A Subquery is used specifically so this
    can never fan out/inflate if the same queryset also carries another
    multi-valued-relation annotation later; it costs exactly one query
    total regardless of how many invoices the queryset returns, so a list
    of N invoices never triggers N extra SUM queries.

    `Payment.objects` is the soft-delete-aware manager (BaseModel), so a
    voided payment is already excluded here -- the same exclusion
    `PaymentRepository.sum_active_amount_for_invoice` relies on.
    """
    paid_subquery = (
        Payment.objects.filter(invoice_id=OuterRef("pk"))
        .values("invoice_id")
        .annotate(total=Sum("amount"))
        .values("total")
    )
    return queryset.annotate(
        paid_amount=Coalesce(
            Subquery(paid_subquery, output_field=DecimalField(max_digits=14, decimal_places=2)),
            Decimal("0.00"),
        )
    )


class InvoiceRepository:
    """
    Data-access layer for Invoice (BE-042). Mirrors
    apps.quotations.repositories.QuotationRepository's shape.
    """

    @staticmethod
    def all_for_project(project_id: str | uuid.UUID) -> QuerySet[Invoice]:
        return with_paid_amount(
            Invoice.objects.select_related("company", "project", "quotation", "client").filter(
                project_id=project_id
            )
        )

    @staticmethod
    def get_by_id(invoice_id: str | uuid.UUID) -> Invoice:
        try:
            return with_paid_amount(
                Invoice.objects.select_related("company", "project", "quotation", "client")
            ).get(id=invoice_id)
        except (Invoice.DoesNotExist, ValueError):
            raise drf_exceptions.NotFound("The requested invoice was not found.")

    @staticmethod
    def create(**fields: Any) -> Invoice:
        return Invoice.objects.create(**fields)

    @staticmethod
    def save(invoice: Invoice, fields: Optional[Dict[str, Any]] = None) -> Invoice:
        for field, value in (fields or {}).items():
            setattr(invoice, field, value)
        invoice.save()
        return invoice

    @staticmethod
    def next_invoice_number(company_id: str | uuid.UUID) -> str:
        """
        Per-company sequential invoice number ("INV-000001") -- the same
        scheme QuotationRepository.next_quote_number established (BE-039),
        applied here without a `version=1` filter since Invoice has no
        versioning concept.
        """
        count = Invoice.objects.filter(company_id=company_id).count()
        return f"INV-{count + 1:06d}"

    @staticmethod
    def get_company_by_id(company_id: str | uuid.UUID) -> Company:
        try:
            return Company.objects.get(id=company_id)
        except (Company.DoesNotExist, ValueError):
            raise drf_exceptions.NotFound("The specified company was not found.")


class InvoiceItemRepository:
    """
    Data-access layer for InvoiceItem (BE-042). No independent get_by_id/
    save/soft_delete -- items have no CRUD endpoint of their own
    (Finance_API.md documents none), only bulk creation as part of
    InvoiceService.create_invoice/update_invoice.
    """

    @staticmethod
    def all_for_invoice(invoice_id: str | uuid.UUID) -> QuerySet[InvoiceItem]:
        return InvoiceItem.objects.filter(invoice_id=invoice_id)

    @staticmethod
    def bulk_create(items: List[InvoiceItem]) -> List[InvoiceItem]:
        return InvoiceItem.objects.bulk_create(items)

    @staticmethod
    def delete_all_for_invoice(invoice_id: str | uuid.UUID) -> None:
        InvoiceItem.objects.filter(invoice_id=invoice_id).delete()
