import uuid
from typing import Any, Dict, Optional

from django.db import transaction
from django.db.models import QuerySet
from django.utils import timezone
from rest_framework import exceptions as drf_exceptions

from apps.audit.models import AuditAction
from apps.audit.services import AuditLogService
from apps.common.exceptions import ConflictError
from apps.projects.validators import validate_assignee_company_membership
from apps.site_visits import selectors, validators
from apps.site_visits.models import SiteVisit
from apps.site_visits.repositories import SiteVisitRepository

AUDITED_FIELDS = (
    "lead_id",
    "project_id",
    "client_id",
    "visit_date",
    "assigned_to_id",
    "address",
    "budget",
    "report_submitted_at",
)


def _serialize_audit_value(value: Any) -> Any:
    """Same JSONField-has-no-custom-encoder reasoning as every other service's audit helper in this codebase (BE-029/BE-033/BE-061/...)."""
    if isinstance(value, uuid.UUID):
        return str(value)
    if hasattr(value, "isoformat"):
        return value.isoformat()
    if hasattr(value, "__str__") and value.__class__.__name__ == "Decimal":
        return str(value)
    return value


def _audit_state(site_visit: SiteVisit) -> Dict[str, Any]:
    return {field: _serialize_audit_value(getattr(site_visit, field)) for field in AUDITED_FIELDS}


class SiteVisitService:
    """
    Business logic and orchestration service for Site Visit management
    (BE-062). Mirrors apps.leads.services.LeadService's structure for
    plain CRUD; `submit_report`'s optional project-creation mirrors
    LeadService.convert_lead's own transactional pattern.
    """

    @classmethod
    def list_site_visits(
        cls,
        company_id: Optional[str | uuid.UUID] = None,
        lead_id: Optional[str | uuid.UUID] = None,
        project_id: Optional[str | uuid.UUID] = None,
        assigned_to_id: Optional[str | uuid.UUID] = None,
        ordering: str = "-visit_date",
    ) -> QuerySet[SiteVisit]:
        return selectors.list_site_visits(
            company_id=company_id,
            lead_id=lead_id,
            project_id=project_id,
            assigned_to_id=assigned_to_id,
            ordering=ordering,
        )

    @classmethod
    def list_site_visits_for_viewer(
        cls,
        is_platform_admin: bool,
        resolved_company_id: Optional[str | uuid.UUID],
        admin_company_id_param: Optional[str],
        lead_id: Optional[str | uuid.UUID] = None,
        project_id: Optional[str | uuid.UUID] = None,
        assigned_to_id: Optional[str | uuid.UUID] = None,
        ordering: str = "-visit_date",
    ) -> QuerySet[SiteVisit]:
        """Mirrors LeadService.list_leads_for_viewer exactly."""
        target_company_id = admin_company_id_param if is_platform_admin else resolved_company_id
        return cls.list_site_visits(
            company_id=target_company_id,
            lead_id=lead_id,
            project_id=project_id,
            assigned_to_id=assigned_to_id,
            ordering=ordering,
        )

    @classmethod
    def resolve_create_target_company_id(
        cls,
        is_platform_admin: bool,
        resolved_company_id: Optional[str | uuid.UUID],
        supplied_company_id: Optional[str | uuid.UUID],
    ) -> str | uuid.UUID:
        """Mirrors LeadService.resolve_create_target_company_id exactly — a client-supplied companyId is never trusted as the authorization boundary (Tenant.md §4)."""
        if is_platform_admin:
            if not supplied_company_id:
                raise drf_exceptions.ValidationError(
                    {"companyId": ["companyId is required for platform admin site visit creation."]}
                )
            return supplied_company_id

        if supplied_company_id and str(supplied_company_id) != str(resolved_company_id):
            raise drf_exceptions.PermissionDenied(
                "You do not have permission to create site visits for this company."
            )
        return resolved_company_id

    @classmethod
    def get_site_visit_by_id(
        cls,
        site_visit_id: str | uuid.UUID,
        company_id: Optional[str | uuid.UUID] = None,
    ) -> SiteVisit:
        """Retrieve an active, non-deleted SiteVisit by primary key UUID. Raises NotFound if it does not exist, is soft-deleted, or belongs to another company."""
        site_visit = SiteVisitRepository.get_by_id(site_visit_id)

        if company_id is not None and str(site_visit.company_id) != str(company_id):
            raise drf_exceptions.NotFound("The requested site visit was not found.")

        return site_visit

    @staticmethod
    def _resolve_lead_project_client(company_id, lead_id, project_id):
        """
        Shared cross-tenant-checked resolution of the lead/project/client
        triad for both create and update. A lead or project belonging to
        another company is treated as not found (Error_Handling.md §5 —
        cross-tenant access is 404, never 403), exactly like every other
        cross-entity reference check in this codebase
        (validate_assignee_company_membership's own sibling checks).
        """
        lead = None
        project = None

        if lead_id:
            lead = SiteVisitRepository.get_lead_by_id(lead_id)
            if str(lead.company_id) != str(company_id):
                raise drf_exceptions.NotFound("The specified lead was not found.")

        if project_id:
            project = SiteVisitRepository.get_project_by_id(project_id)
            if str(project.company_id) != str(company_id):
                raise drf_exceptions.NotFound("The specified project was not found.")

        client = None
        if project is not None:
            client = project.client
        elif lead is not None and lead.converted_client_id:
            client = lead.converted_client

        return lead, project, client

    @classmethod
    def create_site_visit(
        cls,
        company_id: str | uuid.UUID,
        visit_date: Any,
        lead_id: Optional[str | uuid.UUID] = None,
        project_id: Optional[str | uuid.UUID] = None,
        assigned_to_id: Optional[str | uuid.UUID] = None,
        address: str = "",
        measurements: str = "",
        requirements: str = "",
        photo_urls: Optional[list] = None,
        video_urls: Optional[list] = None,
        notes: str = "",
        budget: Any = None,
        site_conditions: str = "",
        follow_up_actions: str = "",
        actor_user: Any = None,
        request: Any = None,
    ) -> SiteVisit:
        """Create a new SiteVisit within a Company tenant, scheduled against a lead and/or a project."""
        with transaction.atomic():
            company = SiteVisitRepository.get_company_by_id(company_id)
            validators.require_lead_or_project(lead_id, project_id)
            lead, project, client = cls._resolve_lead_project_client(company_id, lead_id, project_id)

            assigned_user = None
            if assigned_to_id:
                validate_assignee_company_membership(assigned_to_id, company_id)
                assigned_user = SiteVisitRepository.get_user_by_id(assigned_to_id)

            site_visit = SiteVisitRepository.create(
                company=company,
                lead=lead,
                project=project,
                client=client,
                visit_date=visit_date,
                assigned_to=assigned_user,
                address=(address or "").strip(),
                measurements=measurements or "",
                requirements=requirements or "",
                photo_urls=photo_urls or [],
                video_urls=video_urls or [],
                notes=notes or "",
                budget=budget,
                site_conditions=site_conditions or "",
                follow_up_actions=follow_up_actions or "",
            )

            AuditLogService.record(
                action=AuditAction.CREATE,
                entity_type="site_visit",
                entity_id=site_visit.id,
                company_id=company.id,
                actor_user=actor_user,
                after_state=_audit_state(site_visit),
                request=request,
            )

            return site_visit

    @classmethod
    def update_site_visit(
        cls,
        site_visit_id: str | uuid.UUID,
        validated_data: Dict[str, Any],
        company_id: Optional[str | uuid.UUID] = None,
        actor_user: Any = None,
        request: Any = None,
    ) -> SiteVisit:
        """
        Update an existing SiteVisit's captured-on-site fields.
        `lead`/`project`/`client` are deliberately not settable here —
        FRS §9 documents no "reassign a site visit" flow, and allowing
        it would let `client` silently drift out of sync with whichever
        lead/project it was resolved from at creation. `reportSubmittedAt`
        is also excluded — it only ever moves via `submit_report`.
        """
        with transaction.atomic():
            site_visit = cls.get_site_visit_by_id(site_visit_id, company_id=company_id)
            before_state = _audit_state(site_visit)

            fields: Dict[str, Any] = {}

            if "visit_date" in validated_data:
                fields["visit_date"] = validated_data["visit_date"]

            for field in ("address", "measurements", "requirements", "notes", "site_conditions", "follow_up_actions"):
                if field in validated_data:
                    value = validated_data[field]
                    fields[field] = (value or "").strip() if isinstance(value, str) else value

            for field in ("photo_urls", "video_urls"):
                if field in validated_data:
                    fields[field] = validated_data[field] or []

            if "budget" in validated_data:
                fields["budget"] = validated_data["budget"]

            if "assigned_to_id" in validated_data:
                assignee_id = validated_data["assigned_to_id"]
                if assignee_id:
                    validate_assignee_company_membership(assignee_id, site_visit.company_id)
                    fields["assigned_to"] = SiteVisitRepository.get_user_by_id(assignee_id)
                else:
                    fields["assigned_to"] = None

            site_visit = SiteVisitRepository.save(site_visit, fields)

            AuditLogService.record(
                action=AuditAction.UPDATE,
                entity_type="site_visit",
                entity_id=site_visit.id,
                company_id=site_visit.company_id,
                actor_user=actor_user,
                before_state=before_state,
                after_state=_audit_state(site_visit),
                request=request,
            )

            return site_visit

    @classmethod
    def soft_delete_site_visit(
        cls,
        site_visit_id: str | uuid.UUID,
        company_id: Optional[str | uuid.UUID] = None,
        actor_user: Any = None,
        request: Any = None,
    ) -> None:
        with transaction.atomic():
            site_visit = cls.get_site_visit_by_id(site_visit_id, company_id=company_id)
            site_visit_id_val = site_visit.id
            company_id_val = site_visit.company_id
            before_state = _audit_state(site_visit)

            SiteVisitRepository.soft_delete(site_visit)

            AuditLogService.record(
                action=AuditAction.DELETE,
                entity_type="site_visit",
                entity_id=site_visit_id_val,
                company_id=company_id_val,
                actor_user=actor_user,
                before_state=before_state,
                request=request,
            )

    @classmethod
    def submit_report(
        cls,
        site_visit_id: str | uuid.UUID,
        create_project: bool = False,
        project_name: Optional[str] = None,
        company_id: Optional[str | uuid.UUID] = None,
        actor_user: Any = None,
        request: Any = None,
    ) -> SiteVisit:
        """
        `POST /site-visits/{id}/report` (04_API/CRM_API.md: "Submit site
        visit report (may trigger project creation)"). Idempotent:
        calling this again on an already-completed visit returns it
        unchanged rather than re-stamping `reportSubmittedAt` or
        double-creating a project.

        `createProject=true` only creates a NEW project when this visit
        has a resolved `client` (from an already-converted lead or an
        existing project link) but no `project` yet — it deliberately
        does NOT also convert a not-yet-converted lead into a client
        (that is LeadService.convert_lead's own, already-idempotent
        responsibility; duplicating it here would risk two divergent
        "become a real client" code paths). Rejects with 409 if
        `createProject` is requested but no client is resolvable yet.

        `client` is re-resolved from `lead.converted_client` here (not
        only at creation time): the realistic flow is schedule a visit
        against a lead, do the visit, THEN convert the lead once it's
        clearly won, then submit the report — a site visit created
        before its lead was converted must not be permanently stuck
        with no client just because that was true at creation time.
        """
        with transaction.atomic():
            site_visit = cls.get_site_visit_by_id(site_visit_id, company_id=company_id)

            if site_visit.is_completed:
                return site_visit

            before_state = _audit_state(site_visit)
            project = site_visit.project

            if not site_visit.client_id and site_visit.lead_id and site_visit.lead.converted_client_id:
                site_visit = SiteVisitRepository.save(site_visit, {"client": site_visit.lead.converted_client})

            if create_project and project is None:
                if not site_visit.client_id:
                    raise ConflictError(
                        "Cannot create a project from this site visit: no client is linked yet "
                        "(convert the lead to a client first)."
                    )

                from apps.projects.services import ProjectService

                project = ProjectService.create_project(
                    company_id=site_visit.company_id,
                    client_id=site_visit.client_id,
                    name=(project_name or f"{site_visit.client.name} Project").strip(),
                    assigned_to_id=site_visit.assigned_to_id,
                    actor_user=actor_user,
                    request=request,
                )

                if site_visit.lead_id and not site_visit.lead.converted_project_id:
                    from apps.leads.repositories import LeadRepository

                    LeadRepository.save(site_visit.lead, {"converted_project": project})

            fields: Dict[str, Any] = {"report_submitted_at": timezone.now()}
            if project is not None:
                fields["project"] = project

            site_visit = SiteVisitRepository.save(site_visit, fields)

            AuditLogService.record(
                action=AuditAction.UPDATE,
                entity_type="site_visit",
                entity_id=site_visit.id,
                company_id=site_visit.company_id,
                actor_user=actor_user,
                before_state=before_state,
                after_state=_audit_state(site_visit),
                request=request,
            )

            return site_visit
