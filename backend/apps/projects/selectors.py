import uuid
from typing import Optional

from django.db.models import QuerySet

from apps.projects.models import TERMINAL_PROJECT_STATUSES, Project
from apps.projects.repositories import ProjectRepository


def list_projects(company_id: Optional[str | uuid.UUID] = None) -> QuerySet[Project]:
    """
    Read-only, company-scoped Project listing for ProjectService.list_projects
    (BE-025). Deliberately bare — no search/status/priority/date-range
    filtering here. Project_API.md documents those as list filters, but
    BE-028 ("Project Filters") owns that logic explicitly as its own task;
    building it here would blur that boundary the same way was avoided
    for Workflow/Audit. company_id=None means no tenant filter, reachable
    only from the Platform Admin surface (Tenant.md §4).
    """
    queryset = ProjectRepository.all()

    if company_id:
        queryset = queryset.filter(company_id=company_id)

    return queryset.order_by("-created_at")


class ProjectSelector:
    """
    Read-only Project-domain queries. BE-024's one real selector
    responsibility: answering whether a Client has any non-terminal
    Project, so apps.clients.services.ClientService.soft_delete_client()
    can enforce the delete guard without apps.clients owning any
    knowledge of Project status semantics (Backend Lead architecture
    decision, 2026-08-27 — Project lifecycle understanding belongs to the
    Project domain, not the Client domain).

    Dependency direction: apps.clients.services imports THIS module, not
    the other way around. This file imports only apps.projects.models
    (its own app) — it does not import anything from apps.clients, so no
    cycle exists: clients -> projects.selectors -> projects.models, and
    projects.models references clients.Client only via the Django string
    app label "clients.Client" on the FK field, which the app registry
    resolves lazily at startup rather than through a Python-level import.
    """

    @staticmethod
    def has_blocking_projects_for_client(client_id: str | uuid.UUID) -> bool:
        """
        True if the given client (by ID) has at least one Project whose
        status is not in TERMINAL_PROJECT_STATUSES (completed/cancelled).
        A single efficient EXISTS query — no related objects are fetched.
        """
        return (
            Project.objects.filter(client_id=client_id)
            .exclude(status__in=TERMINAL_PROJECT_STATUSES)
            .exists()
        )
