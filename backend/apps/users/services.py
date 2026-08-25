import logging
import uuid
from typing import Any, Dict, Iterable, Optional
from django.db import transaction
from django.db.models import Q, QuerySet
from rest_framework import exceptions as drf_exceptions

from apps.common.exceptions import ConflictError
from apps.company.models import Company
from apps.users.models import Role

logger = logging.getLogger("apps.users.services")
audit_logger = logging.getLogger("apps.users.audit")


class RoleService:
    """
    Business logic and orchestration service for Role management.
    Adheres to Folder_Structure.md §2: controllers contain no business logic;
    all data operations and validations run through RoleService.
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
        queryset = Role.objects.select_related("company").all()

        if company_id:
            queryset = queryset.filter(company_id=company_id)
        elif company_ids is not None:
            queryset = queryset.filter(company_id__in=company_ids)

        if is_active is not None:
            queryset = queryset.filter(is_active=is_active)

        if search:
            search_query = search.strip()
            queryset = queryset.filter(
                Q(name__icontains=search_query) | Q(description__icontains=search_query)
            )

        valid_order_fields = {
            "created_at",
            "-created_at",
            "name",
            "-name",
            "updated_at",
            "-updated_at",
            "is_active",
            "-is_active",
        }
        if ordering in valid_order_fields:
            queryset = queryset.order_by(ordering)
        else:
            queryset = queryset.order_by("-created_at")

        return queryset

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
        try:
            role = Role.objects.select_related("company").get(id=role_id)
        except (Role.DoesNotExist, ValueError):
            raise drf_exceptions.NotFound("The requested role was not found.")

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
    ) -> Role:
        """
        Create a new Role within a Company tenant.
        Enforces name uniqueness per company among active records and transaction atomicity.
        """
        with transaction.atomic():
            # Validate target company exists and is active
            try:
                company = Company.objects.get(id=company_id)
            except (Company.DoesNotExist, ValueError):
                raise drf_exceptions.NotFound("The specified company was not found.")

            cleaned_name = name.strip()
            if not cleaned_name:
                raise drf_exceptions.ValidationError({"name": ["Role name cannot be blank or empty."]})

            # Enforce unique active role name per company
            if Role.objects.filter(
                company_id=company.id,
                name__iexact=cleaned_name,
            ).exists():
                raise ConflictError("A role with this name already exists for this company.")

            role = Role.objects.create(
                company=company,
                name=cleaned_name,
                description=description.strip() if description else "",
                is_active=is_active,
            )

            # Audit logging
            actor_id = getattr(actor_user, "id", None)
            audit_logger.info(
                "Role created",
                extra={
                    "action": "create",
                    "entity_type": "role",
                    "entity_id": str(role.id),
                    "company_id": str(company.id),
                    "actor_user_id": str(actor_id) if actor_id else None,
                    "new_value": {
                        "name": role.name,
                        "description": role.description,
                        "is_active": role.is_active,
                    },
                },
            )

            return role

    @classmethod
    def update_role(
        cls,
        role_id: str | uuid.UUID,
        validated_data: Dict[str, Any],
        company_id: Optional[str | uuid.UUID] = None,
        actor_user: Any = None,
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

            if "name" in validated_data:
                new_name = validated_data["name"].strip()
                if not new_name:
                    raise drf_exceptions.ValidationError({"name": ["Role name cannot be blank or empty."]})

                if new_name.lower() != role.name.lower():
                    if Role.objects.filter(
                        company_id=role.company_id,
                        name__iexact=new_name,
                    ).exclude(id=role.id).exists():
                        raise ConflictError("A role with this name already exists for this company.")

                role.name = new_name

            if "description" in validated_data:
                role.description = (
                    validated_data["description"].strip()
                    if validated_data["description"]
                    else ""
                )

            if "is_active" in validated_data:
                role.is_active = validated_data["is_active"]

            role.save()

            # Audit logging
            actor_id = getattr(actor_user, "id", None)
            audit_logger.info(
                "Role updated",
                extra={
                    "action": "update",
                    "entity_type": "role",
                    "entity_id": str(role.id),
                    "company_id": str(role.company_id),
                    "actor_user_id": str(actor_id) if actor_id else None,
                    "old_value": old_value,
                    "new_value": {
                        "name": role.name,
                        "description": role.description,
                        "is_active": role.is_active,
                    },
                },
            )

            return role

    @classmethod
    def soft_delete_role(
        cls,
        role_id: str | uuid.UUID,
        company_id: Optional[str | uuid.UUID] = None,
        actor_user: Any = None,
    ) -> None:
        """
        Soft-delete a Role by setting deleted_at timestamp.
        """
        with transaction.atomic():
            role = cls.get_role_by_id(role_id, company_id=company_id)
            role_id_str = str(role.id)
            company_id_str = str(role.company_id)
            role_name = role.name

            role.delete()

            # Audit logging
            actor_id = getattr(actor_user, "id", None)
            audit_logger.info(
                "Role deleted",
                extra={
                    "action": "delete",
                    "entity_type": "role",
                    "entity_id": role_id_str,
                    "company_id": company_id_str,
                    "actor_user_id": str(actor_id) if actor_id else None,
                    "old_value": {
                        "name": role_name,
                    },
                },
            )
