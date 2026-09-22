import uuid
from typing import Any, Dict, Optional

from django.db import transaction
from django.db.models import QuerySet
from rest_framework import exceptions as drf_exceptions

from apps.audit.models import AuditAction
from apps.audit.services import AuditLogService
from apps.clients.services import ClientService
from apps.common.exceptions import ConflictError
from apps.leads import selectors, validators
from apps.leads.models import Lead, LeadStatus, TERMINAL_LEAD_STATUSES, get_allowed_next_statuses
from apps.leads.repositories import LeadRepository
from apps.projects.validators import validate_assignee_company_membership

AUDITED_FIELDS = (
    "name",
    "company_name",
    "email",
    "mobile",
    "source",
    "status",
    "assigned_to_id",
    "loss_reason",
    "follow_up_reminder_at",
    "converted_client_id",
    "converted_project_id",
)


def _serialize_audit_value(value: Any) -> Any:
    """Same JSONField-has-no-custom-encoder reasoning as every other service's audit helper in this codebase (BE-029/BE-033/...)."""
    if isinstance(value, uuid.UUID):
        return str(value)
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value


def _audit_state(lead: Lead) -> Dict[str, Any]:
    return {field: _serialize_audit_value(getattr(lead, field)) for field in AUDITED_FIELDS}


class LeadService:
    """
    Business logic and orchestration service for Lead management (BE-061).
    Mirrors apps.clients.services.ClientService's structure exactly for
    plain CRUD; status transitions mirror apps.projects.services.
    ProjectService.transition_status's pattern (BE-027).
    """

    @classmethod
    def list_leads(
        cls,
        company_id: Optional[str | uuid.UUID] = None,
        status: Optional[str] = None,
        assigned_to_id: Optional[str | uuid.UUID] = None,
        search: Optional[str] = None,
        ordering: str = "-created_at",
    ) -> QuerySet[Lead]:
        return selectors.list_leads(
            company_id=company_id,
            status=status,
            assigned_to_id=assigned_to_id,
            search=search,
            ordering=ordering,
        )

    @classmethod
    def list_leads_for_viewer(
        cls,
        is_platform_admin: bool,
        resolved_company_id: Optional[str | uuid.UUID],
        admin_company_id_param: Optional[str],
        status: Optional[str] = None,
        assigned_to_id: Optional[str | uuid.UUID] = None,
        search: Optional[str] = None,
        ordering: str = "-created_at",
    ) -> QuerySet[Lead]:
        """Mirrors ClientService.list_clients_for_viewer exactly."""
        target_company_id = admin_company_id_param if is_platform_admin else resolved_company_id
        return cls.list_leads(
            company_id=target_company_id,
            status=status,
            assigned_to_id=assigned_to_id,
            search=search,
            ordering=ordering,
        )

    @classmethod
    def resolve_create_target_company_id(
        cls,
        is_platform_admin: bool,
        resolved_company_id: Optional[str | uuid.UUID],
        supplied_company_id: Optional[str | uuid.UUID],
    ) -> str | uuid.UUID:
        """Mirrors ClientService.resolve_create_target_company_id exactly — a client-supplied companyId is never trusted as the authorization boundary (Tenant.md §4)."""
        if is_platform_admin:
            if not supplied_company_id:
                raise drf_exceptions.ValidationError(
                    {"companyId": ["companyId is required for platform admin lead creation."]}
                )
            return supplied_company_id

        if supplied_company_id and str(supplied_company_id) != str(resolved_company_id):
            raise drf_exceptions.PermissionDenied(
                "You do not have permission to create leads for this company."
            )
        return resolved_company_id

    @classmethod
    def get_lead_by_id(
        cls,
        lead_id: str | uuid.UUID,
        company_id: Optional[str | uuid.UUID] = None,
    ) -> Lead:
        """Retrieve an active, non-deleted Lead by primary key UUID. Raises NotFound if it does not exist, is soft-deleted, or belongs to another company."""
        lead = LeadRepository.get_by_id(lead_id)

        if company_id is not None and str(lead.company_id) != str(company_id):
            raise drf_exceptions.NotFound("The requested lead was not found.")

        return lead

    @classmethod
    def create_lead(
        cls,
        company_id: str | uuid.UUID,
        name: str,
        company_name: str = "",
        email: str = "",
        mobile: str = "",
        source: str = "",
        assigned_to_id: Optional[str | uuid.UUID] = None,
        follow_up_reminder_at: Any = None,
        notes: str = "",
        actor_user: Any = None,
        request: Any = None,
    ) -> Lead:
        """Create a new Lead within a Company tenant, always starting at LeadStatus.NEW."""
        with transaction.atomic():
            company = LeadRepository.get_company_by_id(company_id)
            cleaned_name = validators.require_name(name)

            assigned_user = None
            if assigned_to_id:
                validate_assignee_company_membership(assigned_to_id, company_id)
                assigned_user = LeadRepository.get_user_by_id(assigned_to_id)

            lead = LeadRepository.create(
                company=company,
                name=cleaned_name,
                company_name=(company_name or "").strip(),
                email=(email or "").strip(),
                mobile=(mobile or "").strip(),
                source=(source or "").strip(),
                status=LeadStatus.NEW,
                assigned_to=assigned_user,
                follow_up_reminder_at=follow_up_reminder_at,
                notes=notes or "",
            )

            AuditLogService.record(
                action=AuditAction.CREATE,
                entity_type="lead",
                entity_id=lead.id,
                company_id=company.id,
                actor_user=actor_user,
                after_state=_audit_state(lead),
                request=request,
            )

            return lead

    @classmethod
    def update_lead(
        cls,
        lead_id: str | uuid.UUID,
        validated_data: Dict[str, Any],
        company_id: Optional[str | uuid.UUID] = None,
        actor_user: Any = None,
        request: Any = None,
    ) -> Lead:
        """
        Update an existing Lead's identity/assignment/notes fields.
        `status` is deliberately not settable here — it has its own
        transition graph and endpoint (LeadService.transition_status/
        mark_lost/convert_lead), matching
        ProjectUpdateSerializer's identical exclusion of `status`.
        """
        with transaction.atomic():
            lead = cls.get_lead_by_id(lead_id, company_id=company_id)
            before_state = _audit_state(lead)

            fields: Dict[str, Any] = {}

            if "name" in validated_data:
                fields["name"] = validators.require_name(validated_data["name"])

            for field in ("company_name", "email", "mobile", "source", "notes"):
                if field in validated_data:
                    value = validated_data[field]
                    fields[field] = (value or "").strip() if isinstance(value, str) else value

            if "follow_up_reminder_at" in validated_data:
                fields["follow_up_reminder_at"] = validated_data["follow_up_reminder_at"]

            if "assigned_to_id" in validated_data:
                assignee_id = validated_data["assigned_to_id"]
                if assignee_id:
                    validate_assignee_company_membership(assignee_id, lead.company_id)
                    fields["assigned_to"] = LeadRepository.get_user_by_id(assignee_id)
                else:
                    fields["assigned_to"] = None

            lead = LeadRepository.save(lead, fields)

            AuditLogService.record(
                action=AuditAction.UPDATE,
                entity_type="lead",
                entity_id=lead.id,
                company_id=lead.company_id,
                actor_user=actor_user,
                before_state=before_state,
                after_state=_audit_state(lead),
                request=request,
            )

            return lead

    @classmethod
    def soft_delete_lead(
        cls,
        lead_id: str | uuid.UUID,
        company_id: Optional[str | uuid.UUID] = None,
        actor_user: Any = None,
        request: Any = None,
    ) -> None:
        """Soft-delete a Lead by setting deleted_at timestamp. Added for CRUD consistency (matches BE-031/BE-035's established precedent), not itself separately documented."""
        with transaction.atomic():
            lead = cls.get_lead_by_id(lead_id, company_id=company_id)
            lead_id_val = lead.id
            company_id_val = lead.company_id
            before_state = _audit_state(lead)

            LeadRepository.soft_delete(lead)

            AuditLogService.record(
                action=AuditAction.DELETE,
                entity_type="lead",
                entity_id=lead_id_val,
                company_id=company_id_val,
                actor_user=actor_user,
                before_state=before_state,
                request=request,
            )

    @classmethod
    def transition_status(
        cls,
        lead_id: str | uuid.UUID,
        target_status: str,
        company_id: Optional[str | uuid.UUID] = None,
        actor_user: Any = None,
        request: Any = None,
    ) -> Lead:
        """
        Transition a Lead's status per the BE-061 transition graph
        (get_allowed_next_statuses). Raises ConflictError (409) if
        target_status is not reachable from the lead's current status —
        mirrors ProjectService.transition_status exactly, including WON
        never being reachable here (see TERMINAL_LEAD_STATUSES' docstring
        — WON only happens via convert_lead below).
        """
        with transaction.atomic():
            lead = cls.get_lead_by_id(lead_id, company_id=company_id)
            current_status = lead.status
            before_state = _audit_state(lead)

            allowed = get_allowed_next_statuses(current_status)
            if target_status not in allowed:
                raise ConflictError(
                    f"Cannot transition lead from '{current_status}' to '{target_status}'."
                )

            lead = LeadRepository.save(lead, {"status": target_status})

            AuditLogService.record(
                action=AuditAction.UPDATE,
                entity_type="lead",
                entity_id=lead.id,
                company_id=lead.company_id,
                actor_user=actor_user,
                before_state=before_state,
                after_state=_audit_state(lead),
                request=request,
            )

            return lead

    @classmethod
    def mark_lost(
        cls,
        lead_id: str | uuid.UUID,
        loss_reason: str,
        follow_up_reminder_at: Any = None,
        company_id: Optional[str | uuid.UUID] = None,
        actor_user: Any = None,
        request: Any = None,
    ) -> Lead:
        """
        `POST /leads/{id}/mark-lost` (04_API/CRM_API.md: "requires loss
        reason, optional follow-up date"). Uses the same transition graph
        as transition_status (LOST is always in `allowed` for any
        non-terminal status), but as its own endpoint/method since it has
        an additional required field the plain status endpoint doesn't
        carry.
        """
        with transaction.atomic():
            lead = cls.get_lead_by_id(lead_id, company_id=company_id)
            current_status = lead.status
            before_state = _audit_state(lead)

            allowed = get_allowed_next_statuses(current_status)
            if LeadStatus.LOST not in allowed:
                raise ConflictError(f"Cannot mark a '{current_status}' lead as lost.")

            cleaned_reason = validators.require_loss_reason(loss_reason)

            fields: Dict[str, Any] = {"status": LeadStatus.LOST, "loss_reason": cleaned_reason}
            if follow_up_reminder_at is not None:
                fields["follow_up_reminder_at"] = follow_up_reminder_at

            lead = LeadRepository.save(lead, fields)

            AuditLogService.record(
                action=AuditAction.UPDATE,
                entity_type="lead",
                entity_id=lead.id,
                company_id=lead.company_id,
                actor_user=actor_user,
                before_state=before_state,
                after_state=_audit_state(lead),
                request=request,
            )

            return lead

    @classmethod
    def convert_lead(
        cls,
        lead_id: str | uuid.UUID,
        create_project: bool = False,
        project_name: Optional[str] = None,
        company_id: Optional[str | uuid.UUID] = None,
        actor_user: Any = None,
        request: Any = None,
    ) -> Lead:
        """
        `POST /leads/{id}/convert` (04_API/CRM_API.md: "Convert lead ->
        client (+ optionally create project)... idempotent and auditable").

        Idempotent: calling this again on an already-converted lead
        (status WON, converted_client already set) returns the existing
        result unchanged rather than raising or creating a second Client
        — the exact behavior CRM_API.md's own note requires. A LOST lead
        can never be converted (409) — there is no "revive a lost lead"
        flow documented, so none is invented.

        This is the ONLY path that ever sets status=WON (see
        TERMINAL_LEAD_STATUSES' docstring) — the real Client (and
        optional Project) are created in the SAME transaction as the
        status flip, so a lead can never end up "won" without a real
        converted_client behind it.
        """
        with transaction.atomic():
            lead = cls.get_lead_by_id(lead_id, company_id=company_id)

            if lead.status == LeadStatus.WON and lead.converted_client_id:
                return lead

            if lead.status == LeadStatus.LOST:
                raise ConflictError("A lost lead cannot be converted.")

            before_state = _audit_state(lead)

            client = ClientService.create_client(
                company_id=lead.company_id,
                name=lead.name,
                company_name=lead.company_name,
                email=lead.email,
                mobile=lead.mobile,
                notes=f"Converted from lead (source: {lead.source or 'unspecified'}).",
                actor_user=actor_user,
                request=request,
            )

            project = None
            if create_project:
                from apps.projects.services import ProjectService

                project = ProjectService.create_project(
                    company_id=lead.company_id,
                    client_id=client.id,
                    name=(project_name or lead.name).strip() or lead.name,
                    assigned_to_id=lead.assigned_to_id,
                    actor_user=actor_user,
                    request=request,
                )

            fields: Dict[str, Any] = {"status": LeadStatus.WON, "converted_client": client}
            if project is not None:
                fields["converted_project"] = project

            lead = LeadRepository.save(lead, fields)

            # Backfill: a site visit scheduled against this lead before it was
            # converted has `client=None` (apps.site_visits.services resolves
            # `client` from `lead.converted_client` only at its own creation
            # time / report-submit time). Without this, a visit whose report
            # was already submitted before the lead got converted is stuck
            # showing no client forever, since submit_report short-circuits
            # on an already-completed visit and never runs its own
            # re-resolution again. Sync it here instead, at the moment the
            # lead's client relationship actually becomes true.
            from apps.site_visits.repositories import SiteVisitRepository

            SiteVisitRepository.all().filter(lead_id=lead.id, client__isnull=True).update(client=client)

            AuditLogService.record(
                action=AuditAction.UPDATE,
                entity_type="lead",
                entity_id=lead.id,
                company_id=lead.company_id,
                actor_user=actor_user,
                before_state=before_state,
                after_state=_audit_state(lead),
                request=request,
            )

            return lead
