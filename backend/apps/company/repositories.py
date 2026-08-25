import uuid
from typing import Any, Dict, Optional

from django.db.models import QuerySet
from rest_framework import exceptions as drf_exceptions

from apps.company.models import Company


class CompanyRepository:
    """
    Data-access layer for Company. Owns all direct ORM reads/writes so
    CompanyService stays free of persistence details (BACKEND_RULES.md:
    View -> Serializer -> Service -> Repository -> Model).
    """

    @staticmethod
    def all() -> QuerySet[Company]:
        return Company.objects.all()

    @staticmethod
    def get_by_id(company_id: str | uuid.UUID) -> Company:
        try:
            return Company.objects.get(id=company_id)
        except (Company.DoesNotExist, ValueError):
            raise drf_exceptions.NotFound("The requested company was not found.")

    @staticmethod
    def create(**fields: Any) -> Company:
        return Company.objects.create(**fields)

    @staticmethod
    def save(company: Company, fields: Optional[Dict[str, Any]] = None) -> Company:
        for field, value in (fields or {}).items():
            setattr(company, field, value)
        company.save()
        return company

    @staticmethod
    def soft_delete(company: Company) -> None:
        company.delete()
