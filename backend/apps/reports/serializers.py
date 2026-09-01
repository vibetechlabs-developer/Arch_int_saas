from rest_framework import serializers


class FinanceReportQuerySerializer(serializers.Serializer):
    """
    Validates `?dateFrom=&dateTo=&projectId=` for both report endpoints
    (BE-045), matching Finance_API.md's documented filter set exactly.
    """

    projectId = serializers.UUIDField(source="project_id", required=False, allow_null=True, default=None)
    dateFrom = serializers.DateField(source="date_from", required=False, allow_null=True, default=None)
    dateTo = serializers.DateField(source="date_to", required=False, allow_null=True, default=None)


class FinanceReportSerializer(serializers.Serializer):
    """
    Output shape for `GET /reports/finance` (BE-045) -- a plain Serializer
    (not a ModelSerializer), matching
    apps.boq.serializers.BOQSummarySerializer's precedent for a computed,
    non-persisted dict.
    """

    revenue = serializers.DecimalField(max_digits=14, decimal_places=2)
    received = serializers.DecimalField(max_digits=14, decimal_places=2)
    receivables = serializers.DecimalField(max_digits=14, decimal_places=2)
    outstanding = serializers.DecimalField(max_digits=14, decimal_places=2)
    expenses = serializers.DecimalField(max_digits=14, decimal_places=2)
    profitLoss = serializers.DecimalField(source="profit_loss", max_digits=14, decimal_places=2)


class ExpenseReportEntrySerializer(serializers.Serializer):
    key = serializers.CharField(allow_null=True)
    label = serializers.CharField(allow_null=True, allow_blank=True)
    total = serializers.DecimalField(max_digits=14, decimal_places=2)


class ExpenseReportSerializer(serializers.Serializer):
    """
    Output shape for `GET /reports/expenses` (BE-045).
    """

    byCategory = ExpenseReportEntrySerializer(many=True)
    byProject = ExpenseReportEntrySerializer(many=True)
    byVendor = ExpenseReportEntrySerializer(many=True)
    byEmployee = ExpenseReportEntrySerializer(many=True)
    byDate = ExpenseReportEntrySerializer(many=True)
