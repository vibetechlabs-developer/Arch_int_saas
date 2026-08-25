import logging
import uuid
from typing import Any, Dict, Iterable, Optional
from django.db import transaction
from django.db.models import QuerySet
from rest_framework import exceptions as drf_exceptions

from apps.audit.models import AuditAction
from apps.audit.services import AuditLogService
from apps.common.exceptions import ConflictError
from apps.users import selectors, validators
from apps.users.models import Role
from apps.users.repositories import RoleRepository

logger = logging.getLogger("apps.users.services")


class RoleService:
    """
    Business logic and orchestration service for Role management.
    Adheres to Folder_Structure.md §2: controllers contain no business logic;
    all data operations and validations run through RoleService, which in
    turn delegates persistence to RoleRepository, read/list queries to
    apps.users.selectors, and input normalization to apps.users.validators.
    """

    @classmethod
    def list_roles(
        cls,
        company_id: Optional[str | uuid.UUID] = None,
        company_ids: Optional[Iterable[str | uuid.UUID]] = None,
        is_active: Optional[bool] = None,
        search: Optional[str] = None,
        ordering: str = "-created_at",
    ) -> QuerySet[Role]:
        """
        List active (non-soft-deleted) roles with optional tenant scoping,
        status filtering, search, and ordering.
        """
        return selectors.list_roles(
            company_id=company_id,
            company_ids=company_ids,
            is_active=is_active,
            search=search,
            ordering=ordering,
        )

    @classmethod
    def get_role_by_id(
        cls,
        role_id: str | uuid.UUID,
        company_id: Optional[str | uuid.UUID] = None,
    ) -> Role:
        """
        Retrieve an active, non-deleted Role by primary key UUID.
        Raises NotFound if role does not exist, is soft-deleted, or belongs to another company.
        """
        role = RoleRepository.get_by_id(role_id)

        if company_id is not None and str(role.company_id) != str(company_id):
            raise drf_exceptions.NotFound("The requested role was not found.")

        return role

    @classmethod
    def create_role(
        cls,
        company_id: str | uuid.UUID,
        name: str,
        description: str = "",
        is_active: bool = True,
        actor_user: Any = None,
        request: Any = None,
    ) -> Role:
        """
        Create a new Role within a Company tenant.
        Enforces name uniqueness per company among active records and transaction atomicity.
        """
        with transaction.atomic():
            company = RoleRepository.get_company_by_id(company_id)
            cleaned_name = validators.clean_role_name(name)

            if RoleRepository.name_exists_for_company(company.id, cleaned_name):
                raise ConflictError("A role with this name already exists for this company.")

            role = RoleRepository.create(
                company=company,
                name=cleaned_name,
                description=validators.clean_role_description(description),
                is_active=is_active,
            )

            AuditLogService.record(
                action=AuditAction.CREATE,
                entity_type="role",
                entity_id=role.id,
                company_id=company.id,
                actor_user=actor_user,
                after_state={
                    "name": role.name,
                    "description": role.description,
                    "is_active": role.is_active,
                },
                request=request,
            )

            return role

    @classmethod
    def update_role(
        cls,
        role_id: str | uuid.UUID,
        validated_data: Dict[str, Any],
        company_id: Optional[str | uuid.UUID] = None,
        actor_user: Any = None,
        request: Any = None,
    ) -> Role:
        """
        Update an existing Role within a Company tenant.
        Enforces name uniqueness and transaction atomicity.
        """
        with transaction.atomic():
            role = cls.get_role_by_id(role_id, company_id=company_id)
            old_value = {
                "name": role.name,
                "description": role.description,
                "is_active": role.is_active,
            }

            fields: Dict[str, Any] = {}

            if "name" in validated_data:
                new_name = validators.clean_role_name(validated_data["name"])
                if new_name.lower() != role.name.lower():
                    if RoleRepository.name_exists_for_company(
                        role.company_id, new_name, exclude_id=role.id
                    ):
                        raise ConflictError("A role with this name already exists for this company.")
                fields["name"] = new_name

            if "description" in validated_data:
                fields["description"] = validators.clean_role_description(
                    validated_data["description"]
                )

            if "is_active" in validated_data:
                fields["is_active"] = validated_data["is_active"]

            role = RoleRepository.save(role, fields)

            AuditLogService.record(
                action=AuditAction.UPDATE,
                entity_type="role",
                entity_id=role.id,
                company_id=role.company_id,
                actor_user=actor_user,
                before_state=old_value,
                after_state={
                    "name": role.name,
                    "description": role.description,
                    "is_active": role.is_active,
                },
                request=request,
            )

            return role

    @classmethod
    def soft_delete_role(
        cls,
        role_id: str | uuid.UUID,
        company_id: Optional[str | uuid.UUID] = None,
        actor_user: Any = None,
        request: Any = None,
    ) -> None:
        """
        Soft-delete a Role by setting deleted_at timestamp.
        """
        with transaction.atomic():
            role = cls.get_role_by_id(role_id, company_id=company_id)
            role_id_val = role.id
            company_id_val = role.company_id
            before_state = {
                "name": role.name,
                "description": role.description,
                "is_active": role.is_active,
            }

            RoleRepository.soft_delete(role)

            AuditLogService.record(
                action=AuditAction.DELETE,
                entity_type="role",
                entity_id=role_id_val,
                company_id=company_id_val,
                actor_user=actor_user,
                before_state=before_state,
                request=request,
            )
