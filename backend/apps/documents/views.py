from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import exceptions as drf_exceptions
from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common import storage as storage_service
from apps.common.responses import ApiResponse
from apps.common.views import ObjectPermission404Mixin
from apps.documents.serializers import (
    DocumentCreateSerializer,
    DocumentListQuerySerializer,
    DocumentSerializer,
    DocumentUploadSerializer,
)
from apps.documents.services import DocumentService, DocumentUploadService
from apps.projects.permissions import ProjectPermission
from apps.projects.services import ProjectService
from apps.users.permissions import is_platform_admin


class DocumentListCreateView(ObjectPermission404Mixin, APIView):
    """
    `GET`/`POST /projects/{projectId}/documents` (BE-046). Reuses
    ProjectPermission directly, matching every nested-under-Project
    resource in this codebase.
    """

    permission_classes = [IsAuthenticated, ProjectPermission]
    permission_code_map = {"get": "document.view", "post": "document.manage"}

    @extend_schema(
        summary="List Project Documents",
        description="List a project's documents, optionally narrowed to one attached entity.",
        parameters=[
            OpenApiParameter(name="entityType", required=False, type=str),
            OpenApiParameter(name="entityId", required=False, type=str),
            OpenApiParameter(name="ordering", required=False, type=str),
        ],
        responses={status.HTTP_200_OK: DocumentSerializer(many=True)},
        tags=["Documents"],
    )
    def get(self, request: Request, project_id: str = None) -> Response:
        project = ProjectService.get_project_by_id(project_id)
        self.check_object_permissions(request, project)

        query = DocumentListQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        validated = query.validated_data

        documents = DocumentService.list_documents_for_project(
            project,
            entity_type=validated["entity_type"],
            entity_id=validated["entity_id"],
            ordering=validated["ordering"],
        )
        serializer = DocumentSerializer(documents, many=True)
        return ApiResponse.success(
            data=serializer.data, request_id=getattr(request, "request_id", None)
        )

    @extend_schema(
        summary="Register Document",
        description="Register a new document (file already uploaded to storage) against a project or one of its entities.",
        request=DocumentCreateSerializer,
        responses={status.HTTP_201_CREATED: DocumentSerializer},
        tags=["Documents"],
    )
    def post(self, request: Request, project_id: str = None) -> Response:
        project = ProjectService.get_project_by_id(project_id)
        self.check_object_permissions(request, project)

        serializer = DocumentCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated = serializer.validated_data

        document = DocumentService.create_document(
            project=project,
            file_url=validated.get("file_url", ""),
            file_storage_key=validated.get("file_storage_key", ""),
            entity_type=validated.get("entity_type"),
            entity_id=validated.get("entity_id"),
            actor_user=request.user,
            request=request,
        )

        response_data = DocumentSerializer(document).data
        return ApiResponse.created(
            data=response_data, request_id=getattr(request, "request_id", None)
        )


class DocumentUploadView(APIView):
    """
    `POST /documents/upload` (BE-078). Deliberately its own top-level
    route, decoupled from any specific Document row -- mirrors
    `apps.products.views.ProductImageUploadView` exactly, adapted for a
    PRIVATE storage scope (no `url` in the response; see
    `DocumentUploadSerializer`). Gated by `document.manage`, the same code
    `POST /projects/{projectId}/documents` already requires.
    """

    permission_classes = [IsAuthenticated, ProjectPermission]
    parser_classes = [MultiPartParser, FormParser]
    permission_code = "document.manage"

    @extend_schema(
        summary="Upload Document File",
        description="Upload a PDF/JPEG/PNG/WEBP file (multipart/form-data, field name `file`, max 20 MB) to private storage. Returns a storage key usable as fileStorageKey on POST /projects/{projectId}/documents.",
        request={"multipart/form-data": {"type": "object", "properties": {"file": {"type": "string", "format": "binary"}}}},
        responses={status.HTTP_201_CREATED: DocumentUploadSerializer},
        tags=["Documents"],
    )
    def post(self, request: Request) -> Response:
        if is_platform_admin(request):
            company_id = request.query_params.get("companyId")
            if not company_id:
                raise drf_exceptions.ValidationError(
                    {"companyId": ["companyId is required for platform admin document upload."]}
                )
        else:
            company_id = request.company_id

        uploaded_file = request.FILES.get("file")
        result = DocumentUploadService.upload_document(company_id=company_id, uploaded_file=uploaded_file)

        response_data = DocumentUploadSerializer(result).data
        return ApiResponse.created(
            data=response_data, request_id=getattr(request, "request_id", None)
        )


class DocumentDownloadView(ObjectPermission404Mixin, APIView):
    """
    `GET /documents/{documentId}/download` (BE-078) -- the only access
    path for a Document uploaded via `POST /documents/upload`. Reuses the
    exact same permission/tenant check as `DocumentDetailView.get`
    (`document.view`), so a caller who can already see the document's
    metadata can also read its bytes, and no one else can. Returns raw
    file bytes (or a redirect to a signed URL, on S3), never the standard
    JSON envelope -- matches the existing PDF-export endpoints' precedent
    (BE-076).
    """

    permission_classes = [IsAuthenticated, ProjectPermission]
    permission_code_map = {"get": "document.view"}

    @extend_schema(
        summary="Download Document",
        description="Stream (or redirect to a signed URL for) a document's stored file. 404 if this document has no stored file (a legacy fileUrl-registered document, or cross-tenant).",
        responses={status.HTTP_200_OK: None},
        tags=["Documents"],
    )
    def get(self, request: Request, document_id: str = None) -> Response:
        document = DocumentService.get_document_by_id(document_id)
        self.check_object_permissions(request, document)

        if not document.file_storage_key:
            raise drf_exceptions.NotFound("This document has no stored file to download.")

        extension = document.file_storage_key.rsplit(".", 1)[-1] if "." in document.file_storage_key else "bin"
        filename = f"document-{document.id}.{extension}"
        return storage_service.private_file_response("documents", document.file_storage_key, filename)


class DocumentDetailView(ObjectPermission404Mixin, APIView):
    """
    `GET`/`DELETE /documents/{documentId}` (BE-046).
    """

    permission_classes = [IsAuthenticated, ProjectPermission]
    permission_code_map = {"get": "document.view", "delete": "document.manage"}

    @extend_schema(
        summary="Get Document",
        responses={status.HTTP_200_OK: DocumentSerializer},
        tags=["Documents"],
    )
    def get(self, request: Request, document_id: str = None) -> Response:
        document = DocumentService.get_document_by_id(document_id)
        self.check_object_permissions(request, document)

        response_data = DocumentSerializer(document).data
        return ApiResponse.success(
            data=response_data, request_id=getattr(request, "request_id", None)
        )

    @extend_schema(
        summary="Delete Document",
        description="Soft-delete a document.",
        responses={status.HTTP_200_OK: None},
        tags=["Documents"],
    )
    def delete(self, request: Request, document_id: str = None) -> Response:
        document = DocumentService.get_document_by_id(document_id)
        self.check_object_permissions(request, document)

        DocumentService.soft_delete_document(document, actor_user=request.user, request=request)
        return ApiResponse.success(
            data={"message": "Document deleted successfully."},
            request_id=getattr(request, "request_id", None),
        )
