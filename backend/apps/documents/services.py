import uuid
from typing import Any, Dict, Optional

from django.db import transaction
from django.db.models import QuerySet
from rest_framework import exceptions as drf_exceptions

from apps.audit.models import AuditAction
from apps.audit.services import AuditLogService
from apps.documents import selectors, validators
from apps.documents.models import Document
from apps.documents.repositories import DocumentRepository
from apps.projects.models import Project

DOCUMENT_AUDITED_FIELDS = ("project_id", "entity_type", "entity_id", "file_url", "version", "uploaded_by_id")


def _serialize_document_audit_value(value: Any) -> Any:
    """
    Same JSONField-has-no-custom-encoder reasoning as every other
    service's audit helper in this codebase (BE-029/BE-033/BE-036/
    BE-039/BE-042/BE-043/BE-044) -- Document's audited fields include
    three UUID FK ids.
    """
    if isinstance(value, uuid.UUID):
        return str(value)
    return value


def _document_audit_state(document: Document) -> Dict[str, Any]:
    return {
        field: _serialize_document_audit_value(getattr(document, field))
        for field in DOCUMENT_AUDITED_FIELDS
    }


class DocumentService:
    """
    Business logic and orchestration service for Document management
    (BE-046).
    """

    @classmethod
    def list_documents_for_project(
        cls,
        project: Project,
        entity_type: Optional[str] = None,
        entity_id: Optional[str | uuid.UUID] = None,
        ordering: str = "-created_at",
    ) -> QuerySet[Document]:
        return selectors.list_documents_for_project(
            project.id, entity_type=entity_type, entity_id=entity_id, ordering=ordering
        )

    @classmethod
    def get_document_by_id(
        cls,
        document_id: str | uuid.UUID,
        company_id: Optional[str | uuid.UUID] = None,
    ) -> Document:
        """
        Retrieve an active, non-deleted Document by primary key UUID.
        Raises NotFound if it does not exist, is soft-deleted, or belongs
        to another company.
        """
        document = DocumentRepository.get_by_id(document_id)

        if company_id is not None and str(document.company_id) != str(company_id):
            raise drf_exceptions.NotFound("The requested document was not found.")

        return document

    @classmethod
    def create_document(
        cls,
        project: Project,
        file_url: str,
        entity_type: Optional[str] = None,
        entity_id: Optional[str | uuid.UUID] = None,
        actor_user: Any = None,
        request: Any = None,
    ) -> Document:
        """
        Register a new Document against an already-authorized Project.
        `entityType`/`entityId` default to `("project", project.id)` when
        omitted -- a document with no more specific target is simply a
        general project document. `version` is auto-assigned: the next
        version among every Document sharing this exact
        (entity_type, entity_id) pair (the same max()+1 pattern
        BOQSectionRepository.max_sort_order_for_boq/
        QuotationRepository.next_quote_number already established) --
        uploading a new file against the same target is how a document
        gets "re-versioned," with no separate endpoint needed.
        """
        with transaction.atomic():
            cleaned_file_url = validators.require_file_url(file_url)

            target_entity_type = entity_type or "project"
            target_entity_id = entity_id or project.id

            next_version = DocumentRepository.max_version_for_entity(target_entity_type, target_entity_id) + 1

            document = DocumentRepository.create(
                company=project.company,
                project=project,
                entity_type=target_entity_type,
                entity_id=target_entity_id,
                file_url=cleaned_file_url,
                version=next_version,
                uploaded_by=actor_user,
            )

            AuditLogService.record(
                action=AuditAction.CREATE,
                entity_type="document",
                entity_id=document.id,
                company_id=project.company_id,
                actor_user=actor_user,
                after_state=_document_audit_state(document),
                request=request,
            )

            return document

    @classmethod
    def soft_delete_document(
        cls,
        document: Document,
        actor_user: Any = None,
        request: Any = None,
    ) -> None:
        with transaction.atomic():
            document_id = document.id
            company_id = document.company_id
            before_state = _document_audit_state(document)

            DocumentRepository.soft_delete(document)

            AuditLogService.record(
                action=AuditAction.DELETE,
                entity_type="document",
                entity_id=document_id,
                company_id=company_id,
                actor_user=actor_user,
                before_state=before_state,
                request=request,
            )
