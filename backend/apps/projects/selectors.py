import datetime
import uuid
from typing import Optional

from django.db.models import QuerySet

from apps.projects.models import TERMINAL_PROJECT_STATUSES, Project
from apps.projects.repositories import ProjectRepository

VALID_ORDER_FIELDS = {
    "created_at",
    "-created_at",
    "updated_at",
    "-updated_at",
    "name",
    "-name",
    "start_date",
    "-start_date",
    "deadline",
    "-deadline",
}


def list_projects(
    company_id: Optional[str | uuid.UUID] = None,
    status: Optional[str] = None,
    client_id: Optional[str | uuid.UUID] = None,
    assigned_to_id: Optional[str | uuid.UUID] = None,
    priority: Optional[str] = None,
    start_date_from: Optional[datetime.date] = None,
    start_date_to: Optional[datetime.date] = None,
    deadline_from: Optional[datetime.date] = None,
    deadline_to: Optional[datetime.date] = None,
    ordering: str = "-created_at",
) -> QuerySet[Project]:
    """
    Read-only, filtered/ordered Project listing for
    ProjectService.list_projects (BE-028). Filters cover exactly
    Project_API.md's documented set ("status, client, assigned user,
    priority, date range") plus ordering, matching the convention already
    established for Client/Role list endpoints. "Date range" is
    undocumented as to which date field it means — Project has two
    (start_date, deadline) — so both are exposed as independent optional
    ranges (startDateFrom/To, deadlineFrom/To) rather than guessing one
    and silently dropping the other (Backend Lead decision, 2026-08-31).
    company_id=None means no tenant filter, reachable only from the
    Platform Admin surface (Tenant.md §4).
    """
    queryset = ProjectRepository.all()

    if company_id:
        queryset = queryset.filter(company_id=company_id)

    if status:
        queryset = queryset.filter(status=status)

    if client_id:
        queryset = queryset.filter(client_id=client_id)

    if assigned_to_id:
        queryset = queryset.filter(assigned_to_id=assigned_to_id)

    if priority:
        queryset = queryset.filter(priority=priority)

    if start_date_from:
        queryset = queryset.filter(start_date__gte=start_date_from)

    if start_date_to:
        queryset = queryset.filter(start_date__lte=start_date_to)

    if deadline_from:
        queryset = queryset.filter(deadline__gte=deadline_from)

    if deadline_to:
        queryset = queryset.filter(deadline__lte=deadline_to)

    order_field = ordering if ordering in VALID_ORDER_FIELDS else "-created_at"
    # "id" is a tie-breaker only (UUIDs carry no ordering meaning) -- without
    # it, rows whose primary order_field value is identical (most commonly
    # created_at, which can collide under coarse OS clock resolution) have
    # no defined relative order, so the same query can return them in a
    # different order across calls/pages. Found via a real flake: identical
    # in isolation, non-deterministic when run inside the full suite.
    return queryset.order_by(order_field, "id")


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
