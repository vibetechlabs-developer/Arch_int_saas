import uuid
from typing import Any

from django.db.models import QuerySet
from rest_framework import exceptions as drf_exceptions

from apps.documents.models import Document


class DocumentRepository:
    """
    Data-access layer for Document (BE-046).
    """

    @staticmethod
    def all_for_project(project_id: str | uuid.UUID) -> QuerySet[Document]:
        return Document.objects.select_related("company", "project", "uploaded_by").filter(
            project_id=project_id
        )

    @staticmethod
    def get_by_id(document_id: str | uuid.UUID) -> Document:
        try:
            return Document.objects.select_related("company", "project", "uploaded_by").get(id=document_id)
        except (Document.DoesNotExist, ValueError):
            raise drf_exceptions.NotFound("The requested document was not found.")

    @staticmethod
    def create(**fields: Any) -> Document:
        return Document.objects.create(**fields)

    @staticmethod
    def soft_delete(document: Document) -> None:
        document.delete()

    @staticmethod
    def max_version_for_entity(entity_type: str, entity_id: str | uuid.UUID) -> int:
        result = (
            Document.objects.filter(entity_type=entity_type, entity_id=entity_id)
            .order_by("-version")
            .values_list("version", flat=True)
            .first()
        )
        return result or 0
