from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.responses import ApiResponse
from apps.common.views import ObjectPermission404Mixin
from apps.documents.serializers import (
    DocumentCreateSerializer,
    DocumentListQuerySerializer,
    DocumentSerializer,
)
from apps.documents.services import DocumentService
from apps.projects.permissions import ProjectPermission
from apps.projects.services import ProjectService


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
            file_url=validated["file_url"],
            entity_type=validated.get("entity_type"),
            entity_id=validated.get("entity_id"),
            actor_user=request.user,
            request=request,
        )

        response_data = DocumentSerializer(document).data
        return ApiResponse.created(
            data=response_data, request_id=getattr(request, "request_id", None)
        )


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
