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
    hasStoredFile = serializers.SerializerMethodField(
        help_text="True when this document was uploaded via POST /documents/upload -- fetch it through GET /documents/{id}/download rather than fileUrl (blank in that case)."
    )
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
            "hasStoredFile",
            "version",
            "uploadedById",
            "uploadedByName",
            "uploadedAt",
        ]
        read_only_fields = fields

    def get_hasStoredFile(self, obj: Document) -> bool:
        return bool(obj.file_storage_key)


class DocumentCreateSerializer(serializers.Serializer):
    """
    Input serializer for `POST /projects/{projectId}/documents`
    (BE-046/BE-078). `entityType`/`entityId` are optional -- omitted, they
    default to `("project", project.id)` in
    DocumentService.create_document. Exactly one of `fileUrl` (legacy
    manual URL registration) / `fileStorageKey` (from a real
    `POST /documents/upload` call) must be supplied --
    validators.require_exactly_one_file_source enforces this in the
    service layer, since which one is "required" depends on the other.
    """

    fileUrl = serializers.URLField(
        source="file_url", required=False, allow_blank=True, default="", max_length=500
    )
    fileStorageKey = serializers.CharField(
        source="file_storage_key",
        required=False,
        allow_blank=True,
        default="",
        max_length=500,
        write_only=True,
        help_text="The `key` returned by POST /documents/upload. Provide this or fileUrl, not both.",
    )
    entityType = serializers.CharField(
        source="entity_type", required=False, allow_blank=True, default="", max_length=50
    )
    entityId = serializers.UUIDField(source="entity_id", required=False, allow_null=True, default=None)


class DocumentUploadSerializer(serializers.Serializer):
    """
    Output shape for `POST /documents/upload` (BE-078, PRIVATE scope) --
    deliberately no `url` field (unlike Product image's PUBLIC-scope
    upload response): a private file has no permanent, publicly-usable
    URL at all. The caller passes `key` back as `fileStorageKey` on
    `POST /projects/{projectId}/documents`, then reads the file back
    later through `GET /documents/{id}/download`.
    """

    key = serializers.CharField()
    fileName = serializers.CharField()
    contentType = serializers.CharField()
    size = serializers.IntegerField()


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
