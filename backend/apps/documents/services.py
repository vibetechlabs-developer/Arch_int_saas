import uuid
from typing import Any, Dict, Optional

from django.db import transaction
from django.db.models import QuerySet
from rest_framework import exceptions as drf_exceptions

from apps.audit.models import AuditAction
from apps.audit.services import AuditLogService
from apps.common import storage as storage_service
from apps.documents import selectors, validators
from apps.documents.models import Document
from apps.documents.repositories import DocumentRepository
from apps.projects.models import Project

DOCUMENT_AUDITED_FIELDS = (
    "project_id",
    "entity_type",
    "entity_id",
    "file_url",
    "file_storage_key",
    "version",
    "uploaded_by_id",
)


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
        file_url: str = "",
        file_storage_key: str = "",
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

        BE-078: exactly one of `file_url` (legacy manual URL) /
        `file_storage_key` (from `POST /documents/upload`) must be
        supplied -- validators.require_exactly_one_file_source enforces
        this.
        """
        with transaction.atomic():
            validators.require_exactly_one_file_source(file_url, file_storage_key)
            cleaned_file_url = file_url.strip() if file_url else ""

            target_entity_type = entity_type or "project"
            target_entity_id = entity_id or project.id

            next_version = DocumentRepository.max_version_for_entity(target_entity_type, target_entity_id) + 1

            document = DocumentRepository.create(
                company=project.company,
                project=project,
                entity_type=target_entity_type,
                entity_id=target_entity_id,
                file_url=cleaned_file_url,
                file_storage_key=file_storage_key or "",
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
        """
        Soft-delete only -- the underlying stored file (when
        `file_storage_key` is set) is deliberately never physically
        deleted here. A Document may be evidence of a signed contract, a
        client approval, or another record with audit/compliance value;
        BE-078's own guidance is explicit that this category of file must
        not be automatically destroyed the way a superseded Product image
        or Company logo is. The row can be restored (`SoftDeleteModel`),
        and the file remains reachable through it if it is.
        """
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


class DocumentUploadService:
    """
    Stores a validated document/receipt file via the shared storage
    abstraction (BE-078, PRIVATE scope "documents") and returns the
    storage `key` the caller then passes back as `fileStorageKey` on
    `POST /projects/{projectId}/documents`. Deliberately no model of its
    own and no `url` in its response -- a private file's actual access
    path is always the authenticated `GET /documents/{id}/download` proxy,
    never a directly resolvable URL. Mirrors
    `apps.products.services.ProductImageService` exactly, adapted for a
    PRIVATE scope.
    """

    @classmethod
    def upload_document(
        cls,
        company_id: str | uuid.UUID,
        uploaded_file: Any,
    ) -> Dict[str, Any]:
        extension, content_type = storage_service.validate_document_upload(uploaded_file)

        storage_key = storage_service.generate_storage_key("documents", company_id, extension)
        storage_service.save_upload("documents", storage_key, uploaded_file)

        return {
            "key": storage_key,
            "fileName": storage_service.safe_display_filename(getattr(uploaded_file, "name", "")),
            "contentType": content_type,
            "size": uploaded_file.size,
        }
