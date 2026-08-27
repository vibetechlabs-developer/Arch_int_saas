from rest_framework import serializers


class HealthCheckResponseSerializer(serializers.Serializer):
    """
    Response body for GET /health/ (BE-020) — the "data" payload inside the
    standard ApiResponse envelope.
    """

    status = serializers.CharField()
