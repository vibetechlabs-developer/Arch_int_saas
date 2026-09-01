import uuid
from typing import Any, Dict, List, Optional

from django.db.models import QuerySet
from rest_framework import exceptions as drf_exceptions

from apps.company.models import Company
from apps.quotations.models import Quotation, QuotationItem


class QuotationRepository:
    """
    Data-access layer for Quotation (BE-039). Mirrors
    apps.boq.repositories.BOQRepository's shape.
    """

    @staticmethod
    def all_for_project(project_id: str | uuid.UUID) -> QuerySet[Quotation]:
        return Quotation.objects.select_related(
            "company", "project", "boq", "client"
        ).filter(project_id=project_id)

    @staticmethod
    def get_by_id(quotation_id: str | uuid.UUID) -> Quotation:
        try:
            return Quotation.objects.select_related(
                "company", "project", "boq", "client"
            ).get(id=quotation_id)
        except (Quotation.DoesNotExist, ValueError):
            raise drf_exceptions.NotFound("The requested quotation was not found.")

    @staticmethod
    def create(**fields: Any) -> Quotation:
        return Quotation.objects.create(**fields)

    @staticmethod
    def save(quotation: Quotation, fields: Optional[Dict[str, Any]] = None) -> Quotation:
        for field, value in (fields or {}).items():
            setattr(quotation, field, value)
        quotation.save()
        return quotation

    @staticmethod
    def get_max_version(company_id: str | uuid.UUID, quote_number: str) -> int:
        result = (
            Quotation.objects.filter(company_id=company_id, quote_number=quote_number)
            .order_by("-version")
            .values_list("version", flat=True)
            .first()
        )
        return result or 0

    @staticmethod
    def next_quote_number(company_id: str | uuid.UUID) -> str:
        """
        Per-company sequential quote number (Backend Lead decision,
        AskUserQuestion, Sprint 5 planning), e.g. "QT-000001". Counts only
        root (version=1) rows so a revision never consumes a new number.
        Same non-atomic max()/count()+1 pattern already accepted in this
        codebase for BOQSectionRepository.max_sort_order_for_boq — a tiny
        concurrent-create race window, not a correctness requirement this
        column needs to enforce (quote_number is a display/reference
        identifier, not a uniqueness-critical key on its own; the real
        uniqueness guarantee is the DB-level
        (company, quote_number, version) constraint on the model).
        """
        count = Quotation.objects.filter(company_id=company_id, version=1).count()
        return f"QT-{count + 1:06d}"

    @staticmethod
    def get_company_by_id(company_id: str | uuid.UUID) -> Company:
        try:
            return Company.objects.get(id=company_id)
        except (Company.DoesNotExist, ValueError):
            raise drf_exceptions.NotFound("The specified company was not found.")


class QuotationItemRepository:
    """
    Data-access layer for QuotationItem (BE-039). No independent
    get_by_id/save/soft_delete — items have no CRUD endpoint of their own
    (Finance_API.md documents none), only bulk creation as part of
    QuotationService.create_quotation/revise_quotation.
    """

    @staticmethod
    def all_for_quotation(quotation_id: str | uuid.UUID) -> QuerySet[QuotationItem]:
        return QuotationItem.objects.select_related("quotation", "product").filter(
            quotation_id=quotation_id
        )

    @staticmethod
    def bulk_create(items: List[QuotationItem]) -> List[QuotationItem]:
        return QuotationItem.objects.bulk_create(items)
