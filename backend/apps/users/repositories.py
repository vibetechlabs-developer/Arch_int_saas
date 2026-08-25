import uuid
from typing import Any, Dict, Optional

from django.db.models import QuerySet
from rest_framework import exceptions as drf_exceptions

from apps.company.models import Company
from apps.users.models import Role


class RoleRepository:
    """
    Data-access layer for Role. Owns all direct ORM reads/writes so
    RoleService stays free of persistence details (BACKEND_RULES.md:
    View -> Serializer -> Service -> Repository -> Model).
    """

    @staticmethod
    def all() -> QuerySet[Role]:
        return Role.objects.select_related("company").all()

    @staticmethod
    def get_by_id(role_id: str | uuid.UUID) -> Role:
        try:
            return Role.objects.select_related("company").get(id=role_id)
        except (Role.DoesNotExist, ValueError):
            raise drf_exceptions.NotFound("The requested role was not found.")

    @staticmethod
    def name_exists_for_company(
        company_id: str | uuid.UUID,
        name: str,
        exclude_id: Optional[str | uuid.UUID] = None,
    ) -> bool:
        queryset = Role.objects.filter(company_id=company_id, name__iexact=name)
        if exclude_id is not None:
            queryset = queryset.exclude(id=exclude_id)
        return queryset.exists()

    @staticmethod
    def create(**fields: Any) -> Role:
        return Role.objects.create(**fields)

    @staticmethod
    def save(role: Role, fields: Optional[Dict[str, Any]] = None) -> Role:
        for field, value in (fields or {}).items():
            setattr(role, field, value)
        role.save()
        return role

    @staticmethod
    def soft_delete(role: Role) -> None:
        role.delete()

    @staticmethod
    def get_company_by_id(company_id: str | uuid.UUID) -> Company:
        try:
            return Company.objects.get(id=company_id)
        except (Company.DoesNotExist, ValueError):
            raise drf_exceptions.NotFound("The specified company was not found.")
