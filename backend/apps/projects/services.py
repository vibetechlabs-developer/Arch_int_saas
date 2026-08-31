import datetime
import uuid
from typing import Any, Dict, Optional
from django.db import IntegrityError, transaction
from django.db.models import QuerySet
from rest_framework import exceptions as drf_exceptions

from apps.audit.models import AuditAction
from apps.audit.services import AuditLogService
from apps.clients.services import ClientService
from apps.common.exceptions import ConflictError
from apps.projects import selectors, validators
from apps.projects.models import Project, ProjectMember, ProjectStatus, get_allowed_next_statuses
from apps.projects.repositories import ProjectMemberRepository, ProjectRepository

PROJECT_AUDITED_FIELDS = (
    "name",
    "client_id",
    "status",
    "priority",
    "assigned_to_id",
    "start_date",
    "deadline",
    "follow_up_reminder_at",
)

PROJECT_MEMBER_AUDITED_FIELDS = ("project_id", "user_id", "assigned_by_id")


def _serialize_audit_value(value: Any) -> Any:
    """
    apps.audit.models.AuditLog.before_state/after_state is a plain
    JSONField with no custom encoder, so it can't serialize a raw
    uuid.UUID/date/datetime the way Project's FK ids and date fields
    naturally are — unlike ClientService's audited fields, which are all
    already strings. Stringify anything json.JSONEncoder can't handle.
    """
    if isinstance(value, (datetime.date, datetime.datetime)):
        return value.isoformat()
    if isinstance(value, uuid.UUID):
        return str(value)
    return value


def _project_audit_state(project: Project) -> Dict[str, Any]:
    return {
        field: _serialize_audit_value(getattr(project, field)) for field in PROJECT_AUDITED_FIELDS
    }


def _project_member_audit_state(member: ProjectMember) -> Dict[str, Any]:
    return {
        field: _serialize_audit_value(getattr(member, field))
        for field in PROJECT_MEMBER_AUDITED_FIELDS
    }


class ProjectService:
    """
    Business logic and orchestration service for Project management
    (BE-025). Mirrors apps.clients.services.ClientService's structure
    (BACKEND_RULES.md: View -> Serializer -> Service -> Repository ->
    Model). No status field is writable through create/update —
    Project_API.md documents a separate dedicated `PATCH .../status`
    endpoint for transitions (BE-027); general create/update never touch
    status. Audit logging (BE-029) mirrors ClientService's pattern exactly.
    """

    @classmethod
    def list_projects(
        cls,
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
        return selectors.list_projects(
            company_id=company_id,
            status=status,
            client_id=client_id,
            assigned_to_id=assigned_to_id,
            priority=priority,
            start_date_from=start_date_from,
            start_date_to=start_date_to,
            deadline_from=deadline_from,
            deadline_to=deadline_to,
            ordering=ordering,
        )

    @classmethod
    def list_projects_for_viewer(
        cls,
        is_platform_admin: bool,
        resolved_company_id: Optional[str | uuid.UUID],
        admin_company_id_param: Optional[str],
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
        Mirrors ClientService.list_clients_for_viewer exactly, extended
        with BE-028's filter set.
        """
        target_company_id = admin_company_id_param if is_platform_admin else resolved_company_id

        return cls.list_projects(
            company_id=target_company_id,
            status=status,
            client_id=client_id,
            assigned_to_id=assigned_to_id,
            priority=priority,
            start_date_from=start_date_from,
            start_date_to=start_date_to,
            deadline_from=deadline_from,
            deadline_to=deadline_to,
            ordering=ordering,
        )

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
        actor_user: Any = None,
        request: Any = None,
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

            AuditLogService.record(
                action=AuditAction.CREATE,
                entity_type="project",
                entity_id=project.id,
                company_id=company.id,
                actor_user=actor_user,
                after_state=_project_audit_state(project),
                request=request,
            )

            return project

    @classmethod
    def update_project(
        cls,
        project_id: str | uuid.UUID,
        validated_data: Dict[str, Any],
        company_id: Optional[str | uuid.UUID] = None,
        actor_user: Any = None,
        request: Any = None,
    ) -> Project:
        """
        Update an existing Project. Only name/dates/priority/assigned_to
        are editable here — client and status are deliberately excluded
        (see class docstring and ProjectUpdateSerializer).
        """
        with transaction.atomic():
            project = cls.get_project_by_id(project_id, company_id=company_id)
            before_state = _project_audit_state(project)

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

            AuditLogService.record(
                action=AuditAction.UPDATE,
                entity_type="project",
                entity_id=project.id,
                company_id=project.company_id,
                actor_user=actor_user,
                before_state=before_state,
                after_state=_project_audit_state(project),
                request=request,
            )

            return project

    @classmethod
    def soft_delete_project(
        cls,
        project_id: str | uuid.UUID,
        company_id: Optional[str | uuid.UUID] = None,
        actor_user: Any = None,
        request: Any = None,
    ) -> None:
        """
        Soft-delete a Project by setting deleted_at timestamp.
        """
        with transaction.atomic():
            project = cls.get_project_by_id(project_id, company_id=company_id)
            project_id_val = project.id
            company_id_val = project.company_id
            before_state = _project_audit_state(project)

            ProjectRepository.soft_delete(project)

            AuditLogService.record(
                action=AuditAction.DELETE,
                entity_type="project",
                entity_id=project_id_val,
                company_id=company_id_val,
                actor_user=actor_user,
                before_state=before_state,
                request=request,
            )

    @classmethod
    def transition_status(
        cls,
        project_id: str | uuid.UUID,
        target_status: str,
        company_id: Optional[str | uuid.UUID] = None,
        actor_user: Any = None,
        request: Any = None,
    ) -> Project:
        """
        Transition a Project's status per the BE-027 transition graph
        (get_allowed_next_statuses). Raises ConflictError (409) if
        target_status is not reachable from the project's current status
        -- this is a state-conflict, not a bad-input error (target_status
        itself is already validated as a real ProjectStatus value by
        ProjectStatusTransitionSerializer before this is called).

        Audited as an UPDATE, not a separate action value — matches
        apps.audit.models.AuditAction's own documented convention ("a
        status change is recorded as an UPDATE with the status field
        visible in before_state/after_state, not a separate action
        value").
        """
        with transaction.atomic():
            project = cls.get_project_by_id(project_id, company_id=company_id)
            current_status = project.status
            before_state = _project_audit_state(project)

            allowed = get_allowed_next_statuses(current_status, project.status_before_hold)
            if target_status not in allowed:
                raise ConflictError(
                    f"Cannot transition project from '{current_status}' to '{target_status}'."
                )

            fields: Dict[str, Any] = {"status": target_status}
            if target_status == ProjectStatus.ON_HOLD:
                fields["status_before_hold"] = current_status
            elif current_status == ProjectStatus.ON_HOLD:
                fields["status_before_hold"] = ""

            project = ProjectRepository.save(project, fields)

            AuditLogService.record(
                action=AuditAction.UPDATE,
                entity_type="project",
                entity_id=project.id,
                company_id=project.company_id,
                actor_user=actor_user,
                before_state=before_state,
                after_state=_project_audit_state(project),
                request=request,
            )

            return project


class ProjectMemberService:
    """
    Business logic for Project team membership (BE-026). Tenant/object
    authorization for the parent Project is enforced at the view layer
    (ProjectService.get_project_by_id + ObjectPermission404Mixin, the same
    pattern ProjectViewSet already uses) — every method here takes an
    already-authorized `project` instance, not a bare ID, so this service
    never needs its own tenant-resolution logic. Audit logging (BE-029)
    records membership rows under entity_type="project_member" (their own
    entity_id), not folded into the parent Project's "project" rows — see
    apps.audit.validators.ENTITY_FIELD_ALLOWLISTS["project_member"].
    """

    @classmethod
    def list_members(cls, project: Project) -> QuerySet[ProjectMember]:
        return ProjectMemberRepository.list_for_project(project.id)

    @classmethod
    def add_member(
        cls,
        project: Project,
        user_id: str | uuid.UUID,
        assigned_by_id: Optional[str | uuid.UUID] = None,
        actor_user: Any = None,
        request: Any = None,
    ) -> ProjectMember:
        """
        Add a user to the project's team.

        Reuses validators.validate_assignee_company_membership — the same
        invariant Project.assigned_to already enforces (BE-025): a team
        member must be an ACTIVE CompanyMembership of the project's
        company. Duplicate active membership is a 409 ConflictError, not a
        validation error, since it's a state conflict rather than bad
        input (mirrors RoleService.create_role's uniqueness handling,
        including the IntegrityError backstop for the TOCTOU race).
        """
        with transaction.atomic():
            validators.validate_assignee_company_membership(user_id, project.company_id)
            user = ProjectMemberRepository.get_user_by_id(user_id)

            if ProjectMemberRepository.active_membership_exists(project.id, user.id):
                raise ConflictError("This user is already a member of this project's team.")

            assigned_by = (
                ProjectMemberRepository.get_user_by_id(assigned_by_id) if assigned_by_id else None
            )

            try:
                with transaction.atomic():
                    member = ProjectMemberRepository.create(
                        company=project.company,
                        project=project,
                        user=user,
                        assigned_by=assigned_by,
                    )
            except IntegrityError as exc:
                raise ConflictError(
                    "This user is already a member of this project's team."
                ) from exc

            AuditLogService.record(
                action=AuditAction.CREATE,
                entity_type="project_member",
                entity_id=member.id,
                company_id=project.company_id,
                actor_user=actor_user,
                after_state=_project_member_audit_state(member),
                request=request,
            )

            return member

    @classmethod
    def remove_member(
        cls,
        project: Project,
        user_id: str | uuid.UUID,
        actor_user: Any = None,
        request: Any = None,
    ) -> None:
        """
        Remove (soft-delete) a user from the project's team. Raises
        NotFound if no active membership exists for this user on this
        project — matching Error_Handling.md's 404 taxonomy for "acting on
        something that isn't there", not a 409.
        """
        with transaction.atomic():
            member = ProjectMemberRepository.get_active_membership(project.id, user_id)
            member_id = member.id
            before_state = _project_member_audit_state(member)

            ProjectMemberRepository.soft_delete(member)

            AuditLogService.record(
                action=AuditAction.DELETE,
                entity_type="project_member",
                entity_id=member_id,
                company_id=project.company_id,
                actor_user=actor_user,
                before_state=before_state,
                request=request,
            )
