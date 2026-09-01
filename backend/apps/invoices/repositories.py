import uuid
from typing import Any, Dict, List, Optional

from django.db.models import QuerySet
from rest_framework import exceptions as drf_exceptions

from apps.company.models import Company
from apps.invoices.models import Invoice, InvoiceItem


class InvoiceRepository:
    """
    Data-access layer for Invoice (BE-042). Mirrors
    apps.quotations.repositories.QuotationRepository's shape.
    """

    @staticmethod
    def all_for_project(project_id: str | uuid.UUID) -> QuerySet[Invoice]:
        return Invoice.objects.select_related("company", "project", "quotation", "client").filter(
            project_id=project_id
        )

    @staticmethod
    def get_by_id(invoice_id: str | uuid.UUID) -> Invoice:
        try:
            return Invoice.objects.select_related("company", "project", "quotation", "client").get(
                id=invoice_id
            )
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
