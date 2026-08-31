from rest_framework import serializers

from apps.boq.models import BOQ, BOQSection


class BOQSectionSerializer(serializers.ModelSerializer):
    """
    Serializer for BOQSection with camelCase JSON fields. `items` is added
    in BE-036 (BOQItem doesn't exist yet in this task).
    """

    boqId = serializers.UUIDField(source="boq_id", read_only=True)
    sortOrder = serializers.IntegerField(source="sort_order", read_only=True)
    createdAt = serializers.DateTimeField(source="created_at", read_only=True)
    updatedAt = serializers.DateTimeField(source="updated_at", read_only=True)

    class Meta:
        model = BOQSection
        fields = ["id", "boqId", "name", "sortOrder", "createdAt", "updatedAt"]
        read_only_fields = ["id", "boqId", "sortOrder", "createdAt", "updatedAt"]


class BOQSectionCreateSerializer(serializers.Serializer):
    """
    Input serializer for `POST .../boq/sections`. No `sortOrder` field —
    auto-assigned server-side (append to end).
    """

    name = serializers.CharField(max_length=255, required=True)

    def validate_name(self, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise serializers.ValidationError("Section name cannot be blank or empty.")
        return cleaned


class BOQSectionUpdateSerializer(serializers.Serializer):
    """
    Input serializer for `PATCH .../boq/sections/{id}` (added for
    consistency, not documented in BOQ_API.md — see BE-031's "add missing
    CRUD" precedent).
    """

    name = serializers.CharField(max_length=255, required=False)

    def validate_name(self, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise serializers.ValidationError("Section name cannot be blank or empty.")
        return cleaned


class BOQSerializer(serializers.ModelSerializer):
    """
    Serializer for the whole BOQ tree — `GET .../boq` returns this,
    including nested sections (and, from BE-036 on, each section's
    items). Read-only end to end: BOQ has no direct create/update
    endpoint of its own (see BOQService.get_or_create_boq_for_project).
    """

    projectId = serializers.UUIDField(source="project_id", read_only=True)
    sections = BOQSectionSerializer(many=True, read_only=True)
    createdAt = serializers.DateTimeField(source="created_at", read_only=True)
    updatedAt = serializers.DateTimeField(source="updated_at", read_only=True)

    class Meta:
        model = BOQ
        fields = ["id", "projectId", "status", "sections", "createdAt", "updatedAt"]
        read_only_fields = fields
