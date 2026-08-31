import uuid
from typing import Any, Dict, Optional
from django.db import transaction
from django.db.models import QuerySet
from rest_framework import exceptions as drf_exceptions

from apps.clients.services import ClientService
from apps.projects import selectors, validators
from apps.projects.models import Project
from apps.projects.repositories import ProjectRepository


class ProjectService:
    """
    Business logic and orchestration service for Project management
    (BE-025). Mirrors apps.clients.services.ClientService's structure
    (BACKEND_RULES.md: View -> Serializer -> Service -> Repository ->
    Model). No audit calls here — Project's own audit integration is
    BE-029's explicit scope, not built prematurely (mirrors how BE-024
    left ENTITY_FIELD_ALLOWLISTS["project"] unbuilt). No status field is
    writable through create/update — Project_API.md documents a separate
    dedicated `PATCH .../status` endpoint for transitions, which is
    BE-027's scope; general create/update never touch status.
    """

    @classmethod
    def list_projects(cls, company_id: Optional[str | uuid.UUID] = None) -> QuerySet[Project]:
        return selectors.list_projects(company_id=company_id)

    @classmethod
    def list_projects_for_viewer(
        cls,
        is_platform_admin: bool,
        resolved_company_id: Optional[str | uuid.UUID],
        admin_company_id_param: Optional[str],
    ) -> QuerySet[Project]:
        """
        Mirrors ClientService.list_clients_for_viewer exactly.
        """
        if is_platform_admin:
            return cls.list_projects(company_id=admin_company_id_param)

        return cls.list_projects(company_id=resolved_company_id)

    @classmethod
    def resolve_create_target_company_id(
        cls,
        is_platform_admin: bool,
        resolved_company_id: Optional[str | uuid.UUID],
        supplied_company_id: Optional[str | uuid.UUID],
    ) -> str | uuid.UUID:
        """
        Mirrors ClientService.resolve_create_target_company_id exactly — a
        client-supplied companyId is never trusted as the authorization
        boundary (Tenant.md §4).
        """
        if is_platform_admin:
            if not supplied_company_id:
                raise drf_exceptions.ValidationError(
                    {"companyId": ["companyId is required for platform admin project creation."]}
                )
            return supplied_company_id

        if supplied_company_id and str(supplied_company_id) != str(resolved_company_id):
            raise drf_exceptions.PermissionDenied(
                "You do not have permission to create projects for this company."
            )
        return resolved_company_id

    @classmethod
    def get_project_by_id(
        cls,
        project_id: str | uuid.UUID,
        company_id: Optional[str | uuid.UUID] = None,
    ) -> Project:
        """
        Retrieve an active, non-deleted Project by primary key UUID.
        Raises NotFound if the project does not exist, is soft-deleted, or
        belongs to another company.
        """
        project = ProjectRepository.get_by_id(project_id)

        if company_id is not None and str(project.company_id) != str(company_id):
            raise drf_exceptions.NotFound("The requested project was not found.")

        return project

    @classmethod
    def create_project(
        cls,
        company_id: str | uuid.UUID,
        client_id: str | uuid.UUID,
        name: str,
        start_date: Any = None,
        deadline: Any = None,
        priority: str = "",
        assigned_to_id: Optional[str | uuid.UUID] = None,
        follow_up_reminder_at: Any = None,
    ) -> Project:
        """
        Create a new Project within a Company tenant.

        Tenant invariant enforcement (resolves BE-024's documented gap):
        the client must belong to the same company — enforced by reusing
        ClientService.get_client_by_id(client_id, company_id=...), which
        already raises NotFound on cross-tenant access (built in BE-023),
        rather than duplicating that check here.
        """
        with transaction.atomic():
            company = ProjectRepository.get_company_by_id(company_id)
            cleaned_name = validators.require_name(name)

            # Raises NotFound if client doesn't exist or belongs to another company.
            client = ClientService.get_client_by_id(client_id, company_id=company_id)

            assigned_user = None
            if assigned_to_id:
                validators.validate_assignee_company_membership(assigned_to_id, company_id)
                assigned_user = ProjectRepository.get_user_by_id(assigned_to_id)

            project = ProjectRepository.create(
                company=company,
                client=client,
                name=cleaned_name,
                start_date=start_date,
                deadline=deadline,
                priority=priority or "",
                assigned_to=assigned_user,
                follow_up_reminder_at=follow_up_reminder_at,
            )

            return project

    @classmethod
    def update_project(
        cls,
        project_id: str | uuid.UUID,
        validated_data: Dict[str, Any],
        company_id: Optional[str | uuid.UUID] = None,
    ) -> Project:
        """
        Update an existing Project. Only name/dates/priority/assigned_to
        are editable here — client and status are deliberately excluded
        (see class docstring and ProjectUpdateSerializer).
        """
        with transaction.atomic():
            project = cls.get_project_by_id(project_id, company_id=company_id)

            fields: Dict[str, Any] = {}

            if "name" in validated_data:
                fields["name"] = validators.require_name(validated_data["name"])

            for field in ("start_date", "deadline", "follow_up_reminder_at"):
                if field in validated_data:
                    fields[field] = validated_data[field]

            if "priority" in validated_data:
                fields["priority"] = validated_data["priority"] or ""

            if "assigned_to_id" in validated_data:
                assigned_to_id = validated_data["assigned_to_id"]
                if assigned_to_id:
                    validators.validate_assignee_company_membership(
                        assigned_to_id, project.company_id
                    )
                    fields["assigned_to"] = ProjectRepository.get_user_by_id(assigned_to_id)
                else:
                    fields["assigned_to"] = None

            project = ProjectRepository.save(project, fields)

            return project

    @classmethod
    def soft_delete_project(
        cls,
        project_id: str | uuid.UUID,
        company_id: Optional[str | uuid.UUID] = None,
    ) -> None:
        """
        Soft-delete a Project by setting deleted_at timestamp.
        """
        with transaction.atomic():
            project = cls.get_project_by_id(project_id, company_id=company_id)
            ProjectRepository.soft_delete(project)
