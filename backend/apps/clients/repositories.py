import uuid
from typing import Any, Dict, Optional

from django.db.models import QuerySet
from rest_framework import exceptions as drf_exceptions

from apps.clients.models import Client


class ClientRepository:
    """
    Data-access layer for Client. Owns all direct ORM reads/writes so
    ClientService stays free of persistence details (BACKEND_RULES.md:
    View -> Serializer -> Service -> Repository -> Model). Mirrors
    apps.users.repositories.RoleRepository.
    """

    @staticmethod
    def all() -> QuerySet[Client]:
        return Client.objects.select_related("company").all()

    @staticmethod
    def get_by_id(client_id: str | uuid.UUID) -> Client:
        try:
            return Client.objects.select_related("company").get(id=client_id)
        except (Client.DoesNotExist, ValueError):
            raise drf_exceptions.NotFound("The requested client was not found.")

    @staticmethod
    def create(**fields: Any) -> Client:
        return Client.objects.create(**fields)

    @staticmethod
    def save(client: Client, fields: Optional[Dict[str, Any]] = None) -> Client:
        for field, value in (fields or {}).items():
            setattr(client, field, value)
        client.save()
        return client

    @staticmethod
    def soft_delete(client: Client) -> None:
        client.delete()
