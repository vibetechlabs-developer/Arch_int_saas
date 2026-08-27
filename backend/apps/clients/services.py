import uuid
from typing import Any, Dict, Optional
from django.db import transaction
from django.db.models import QuerySet
from rest_framework import exceptions as drf_exceptions

from apps.audit.models import AuditAction
from apps.audit.services import AuditLogService
from apps.clients import selectors, validators
from apps.clients.models import Client
from apps.clients.repositories import ClientRepository


AUDITED_FIELDS = ("name", "company_name", "email", "mobile", "gstin")


def _audit_state(client: Client) -> Dict[str, Any]:
    return {field: getattr(client, field) for field in AUDITED_FIELDS}


class ClientService:
    """
    Business logic and orchestration service for Client management.
    Mirrors apps.users.services.RoleService's structure (BACKEND_RULES.md:
    View -> Serializer -> Service -> Repository -> Model). Unlike Role,
    Client has no uniqueness constraint, so no IntegrityError/ConflictError
    handling is needed here — a deliberate simplification, not an omission.
    """

    @classmethod
    def list_clients(
        cls,
        company_id: Optional[str | uuid.UUID] = None,
        search: Optional[str] = None,
        ordering: str = "-created_at",
    ) -> QuerySet[Client]:
        """
        List active (non-soft-deleted) clients with optional tenant
        scoping, search, and ordering. company_id=None means "no tenant
        filter" — reachable only from the Platform Admin surface, matching
        RoleService.list_roles / Tenant.md §4's ban on a "list across
        companies" mode for a company-scoped resource.
        """
        return selectors.list_clients(
            company_id=company_id,
            search=search,
            ordering=ordering,
        )

    @classmethod
    def list_clients_for_viewer(
        cls,
        is_platform_admin: bool,
        resolved_company_id: Optional[str | uuid.UUID],
        admin_company_id_param: Optional[str],
        search: Optional[str] = None,
        ordering: str = "-created_at",
    ) -> QuerySet[Client]:
        """
        Resolve which company_id list_clients() filters by, given the
        caller's admin status. Mirrors
        RoleService.list_roles_for_viewer exactly.
        """
        if is_platform_admin:
            return cls.list_clients(
                company_id=admin_company_id_param,
                search=search,
                ordering=ordering,
            )

        return cls.list_clients(
            company_id=resolved_company_id,
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
        """
        Resolve which company a new Client is created in. Mirrors
        RoleService.resolve_create_target_company_id exactly — a client-
        supplied companyId is never trusted as the authorization boundary
        (Tenant.md §4): for a non-admin it must match resolved_company_id
        exactly, or the request is rejected outright.
        """
        if is_platform_admin:
            if not supplied_company_id:
                raise drf_exceptions.ValidationError(
                    {"companyId": ["companyId is required for platform admin client creation."]}
                )
            return supplied_company_id

        if supplied_company_id and str(supplied_company_id) != str(resolved_company_id):
            raise drf_exceptions.PermissionDenied(
                "You do not have permission to create clients for this company."
            )
        return resolved_company_id

    @classmethod
    def get_client_by_id(
        cls,
        client_id: str | uuid.UUID,
        company_id: Optional[str | uuid.UUID] = None,
    ) -> Client:
        """
        Retrieve an active, non-deleted Client by primary key UUID.
        Raises NotFound if the client does not exist, is soft-deleted, or
        belongs to another company.
        """
        client = ClientRepository.get_by_id(client_id)

        if company_id is not None and str(client.company_id) != str(company_id):
            raise drf_exceptions.NotFound("The requested client was not found.")

        return client

    @classmethod
    def create_client(
        cls,
        company_id: str | uuid.UUID,
        name: str,
        company_name: str = "",
        email: str = "",
        mobile: str = "",
        gstin: str = "",
        addresses: Optional[list] = None,
        notes: str = "",
        actor_user: Any = None,
        request: Any = None,
    ) -> Client:
        """
        Create a new Client within a Company tenant.
        """
        with transaction.atomic():
            company = ClientRepository.get_company_by_id(company_id)
            cleaned_name = validators.require_name(name)

            client = ClientRepository.create(
                company=company,
                name=cleaned_name,
                company_name=(company_name or "").strip(),
                email=(email or "").strip(),
                mobile=(mobile or "").strip(),
                gstin=(gstin or "").strip(),
                addresses=addresses if addresses is not None else [],
                notes=notes or "",
            )

            AuditLogService.record(
                action=AuditAction.CREATE,
                entity_type="client",
                entity_id=client.id,
                company_id=company.id,
                actor_user=actor_user,
                after_state=_audit_state(client),
                request=request,
            )

            return client

    @classmethod
    def update_client(
        cls,
        client_id: str | uuid.UUID,
        validated_data: Dict[str, Any],
        company_id: Optional[str | uuid.UUID] = None,
        actor_user: Any = None,
        request: Any = None,
    ) -> Client:
        """
        Update an existing Client within a Company tenant.
        """
        with transaction.atomic():
            client = cls.get_client_by_id(client_id, company_id=company_id)
            before_state = _audit_state(client)

            fields: Dict[str, Any] = {}

            if "name" in validated_data:
                fields["name"] = validators.require_name(validated_data["name"])

            for field in ("company_name", "email", "mobile", "gstin", "notes"):
                if field in validated_data:
                    value = validated_data[field]
                    fields[field] = (value or "").strip() if isinstance(value, str) else value

            if "addresses" in validated_data:
                fields["addresses"] = validated_data["addresses"]

            client = ClientRepository.save(client, fields)

            AuditLogService.record(
                action=AuditAction.UPDATE,
                entity_type="client",
                entity_id=client.id,
                company_id=client.company_id,
                actor_user=actor_user,
                before_state=before_state,
                after_state=_audit_state(client),
                request=request,
            )

            return client

    @classmethod
    def soft_delete_client(
        cls,
        client_id: str | uuid.UUID,
        company_id: Optional[str | uuid.UUID] = None,
        actor_user: Any = None,
        request: Any = None,
    ) -> None:
        """
        Soft-delete a Client by setting deleted_at timestamp.

        Deferred (BE-024): CRM_API.md's "block delete if active projects
        exist" rule cannot be implemented until the Project model exists —
        Client has no reverse relation to check against yet. This is an
        unconditional soft-delete for now.
        """
        with transaction.atomic():
            client = cls.get_client_by_id(client_id, company_id=company_id)
            client_id_val = client.id
            company_id_val = client.company_id
            before_state = _audit_state(client)

            ClientRepository.soft_delete(client)

            AuditLogService.record(
                action=AuditAction.DELETE,
                entity_type="client",
                entity_id=client_id_val,
                company_id=company_id_val,
                actor_user=actor_user,
                before_state=before_state,
                request=request,
            )
