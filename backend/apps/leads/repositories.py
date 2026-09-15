import uuid
from typing import Any, Dict, Optional

from django.db.models import QuerySet
from rest_framework import exceptions as drf_exceptions

from apps.company.models import Company
from apps.leads.models import Lead
from apps.users.models import User


class LeadRepository:
    """
    Data-access layer for Lead. Owns all direct ORM reads/writes so
    LeadService stays free of persistence details (BACKEND_RULES.md:
    View -> Serializer -> Service -> Repository -> Model). Mirrors
    apps.clients.repositories.ClientRepository.
    """

    @staticmethod
    def all() -> QuerySet[Lead]:
        return Lead.objects.select_related("company", "assigned_to", "converted_client", "converted_project")

    @staticmethod
    def get_by_id(lead_id: str | uuid.UUID) -> Lead:
        try:
            return LeadRepository.all().get(id=lead_id)
        except (Lead.DoesNotExist, ValueError):
            raise drf_exceptions.NotFound("The requested lead was not found.")

    @staticmethod
    def create(**fields: Any) -> Lead:
        return Lead.objects.create(**fields)

    @staticmethod
    def save(lead: Lead, fields: Optional[Dict[str, Any]] = None) -> Lead:
        for field, value in (fields or {}).items():
            setattr(lead, field, value)
        lead.save()
        return lead

    @staticmethod
    def soft_delete(lead: Lead) -> None:
        lead.delete()

    @staticmethod
    def get_company_by_id(company_id: str | uuid.UUID) -> Company:
        try:
            return Company.objects.get(id=company_id)
        except (Company.DoesNotExist, ValueError):
            raise drf_exceptions.NotFound("The specified company was not found.")

    @staticmethod
    def get_user_by_id(user_id: str | uuid.UUID) -> User:
        try:
            return User.objects.get(id=user_id)
        except (User.DoesNotExist, ValueError):
            raise drf_exceptions.NotFound("The specified user was not found.")
