import uuid
from typing import Optional

from django.db.models import QuerySet

from apps.documents.models import Document

VALID_DOCUMENT_ORDER_FIELDS = {
    "created_at",
    "-created_at",
    "version",
    "-version",
}


def list_documents_for_project(
    project_id: str | uuid.UUID,
    entity_type: Optional[str] = None,
    entity_id: Optional[str | uuid.UUID] = None,
    ordering: str = "-created_at",
) -> QuerySet[Document]:
    """
    Read-only Document listing scoped to one already-authorized Project
    (BE-046), optionally narrowed to one specific attached entity.
    """
    queryset = Document.objects.select_related("company", "project", "uploaded_by").filter(
        project_id=project_id
    )

    if entity_type:
        queryset = queryset.filter(entity_type=entity_type)
    if entity_id:
        queryset = queryset.filter(entity_id=entity_id)

    order_field = ordering if ordering in VALID_DOCUMENT_ORDER_FIELDS else "-created_at"
    return queryset.order_by(order_field, "id")
