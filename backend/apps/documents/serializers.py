from rest_framework import serializers

from apps.documents.models import Document
from apps.documents.selectors import VALID_DOCUMENT_ORDER_FIELDS


class DocumentSerializer(serializers.ModelSerializer):
    """
    Output serializer for Document, with camelCase JSON fields matching
    every other serializer in this codebase. `uploadedAt` aliases
    `created_at` -- see Document's model docstring for why no separate
    column exists for it.
    """

    companyId = serializers.UUIDField(source="company_id", read_only=True)
    projectId = serializers.UUIDField(source="project_id", read_only=True)
    entityType = serializers.CharField(source="entity_type", read_only=True)
    entityId = serializers.UUIDField(source="entity_id", read_only=True)
    fileUrl = serializers.URLField(source="file_url", read_only=True)
    uploadedById = serializers.UUIDField(source="uploaded_by_id", read_only=True, allow_null=True)
    uploadedByName = serializers.CharField(
        source="uploaded_by.name", read_only=True, allow_null=True, default=None
    )
    uploadedAt = serializers.DateTimeField(source="created_at", read_only=True)

    class Meta:
        model = Document
        fields = [
            "id",
            "companyId",
            "projectId",
            "entityType",
            "entityId",
            "fileUrl",
            "version",
            "uploadedById",
            "uploadedByName",
            "uploadedAt",
        ]
        read_only_fields = fields


class DocumentCreateSerializer(serializers.Serializer):
    """
    Input serializer for `POST /projects/{projectId}/documents` (BE-046).
    `entityType`/`entityId` are optional -- omitted, they default to
    `("project", project.id)` in DocumentService.create_document.
    """

    fileUrl = serializers.URLField(source="file_url", required=True, max_length=500)
    entityType = serializers.CharField(
        source="entity_type", required=False, allow_blank=True, default="", max_length=50
    )
    entityId = serializers.UUIDField(source="entity_id", required=False, allow_null=True, default=None)


class DocumentListQuerySerializer(serializers.Serializer):
    """
    Validates GET /projects/{projectId}/documents query params (BE-046):
    optional entityType/entityId narrowing, plus ordering.
    """

    entityType = serializers.CharField(
        source="entity_type", required=False, allow_blank=True, default=None, allow_null=True
    )
    entityId = serializers.UUIDField(source="entity_id", required=False, default=None, allow_null=True)
    ordering = serializers.ChoiceField(
        choices=sorted(VALID_DOCUMENT_ORDER_FIELDS), required=False, default="-created_at"
    )
