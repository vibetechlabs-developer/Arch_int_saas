import uuid
from typing import Any, Dict, Optional

from django.db.models import QuerySet
from rest_framework import exceptions as drf_exceptions

from apps.clients.models import Client
from apps.company.models import Company
from apps.leads.models import Lead
from apps.projects.models import Project
from apps.site_visits.models import SiteVisit
from apps.users.models import User


class SiteVisitRepository:
    """
    Data-access layer for SiteVisit. Mirrors apps.leads.repositories.LeadRepository.
    """

    @staticmethod
    def all() -> QuerySet[SiteVisit]:
        return SiteVisit.objects.select_related("company", "lead", "project", "client", "assigned_to")

    @staticmethod
    def get_by_id(site_visit_id: str | uuid.UUID) -> SiteVisit:
        try:
            return SiteVisitRepository.all().get(id=site_visit_id)
        except (SiteVisit.DoesNotExist, ValueError):
            raise drf_exceptions.NotFound("The requested site visit was not found.")

    @staticmethod
    def create(**fields: Any) -> SiteVisit:
        return SiteVisit.objects.create(**fields)

    @staticmethod
    def save(site_visit: SiteVisit, fields: Optional[Dict[str, Any]] = None) -> SiteVisit:
        for field, value in (fields or {}).items():
            setattr(site_visit, field, value)
        site_visit.save()
        return site_visit

    @staticmethod
    def soft_delete(site_visit: SiteVisit) -> None:
        site_visit.delete()

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

    @staticmethod
    def get_lead_by_id(lead_id: str | uuid.UUID) -> Lead:
        try:
            return Lead.objects.get(id=lead_id)
        except (Lead.DoesNotExist, ValueError):
            raise drf_exceptions.NotFound("The specified lead was not found.")

    @staticmethod
    def get_project_by_id(project_id: str | uuid.UUID) -> Project:
        try:
            return Project.objects.get(id=project_id)
        except (Project.DoesNotExist, ValueError):
            raise drf_exceptions.NotFound("The specified project was not found.")

    @staticmethod
    def get_client_by_id(client_id: str | uuid.UUID) -> Client:
        try:
            return Client.objects.get(id=client_id)
        except (Client.DoesNotExist, ValueError):
            raise drf_exceptions.NotFound("The specified client was not found.")
