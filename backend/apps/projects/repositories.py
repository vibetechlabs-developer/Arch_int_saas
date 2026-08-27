import uuid
from typing import Any, Dict, Optional

from django.db.models import QuerySet
from rest_framework import exceptions as drf_exceptions

from apps.projects.models import Project


class ProjectRepository:
    """
    Data-access layer for Project. Owns all direct ORM reads/writes so a
    future ProjectService stays free of persistence details
    (BACKEND_RULES.md: View -> Serializer -> Service -> Repository ->
    Model). Mirrors apps.clients.repositories.ClientRepository's shape at
    the point BE-022 first introduced it — only the methods BE-024 itself
    needs (via ProjectSelector) are included; company/client lookup
    helpers are added when the task that first needs them (project
    creation) is built, matching how ClientRepository grew its own
    get_company_by_id only when BE-023 needed it, not before.
    """

    @staticmethod
    def all() -> QuerySet[Project]:
        return Project.objects.select_related("company", "client").all()

    @staticmethod
    def get_by_id(project_id: str | uuid.UUID) -> Project:
        try:
            return Project.objects.select_related("company", "client").get(id=project_id)
        except (Project.DoesNotExist, ValueError):
            raise drf_exceptions.NotFound("The requested project was not found.")

    @staticmethod
    def create(**fields: Any) -> Project:
        return Project.objects.create(**fields)

    @staticmethod
    def save(project: Project, fields: Optional[Dict[str, Any]] = None) -> Project:
        for field, value in (fields or {}).items():
            setattr(project, field, value)
        project.save()
        return project

    @staticmethod
    def soft_delete(project: Project) -> None:
        project.delete()
