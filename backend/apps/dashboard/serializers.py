from rest_framework import serializers

from apps.audit.serializers import AuditLogSerializer


class DashboardKPISerializer(serializers.Serializer):
    totalProjects = serializers.IntegerField()
    activeProjects = serializers.IntegerField()
    totalQuotations = serializers.IntegerField()
    totalBilledRevenue = serializers.DecimalField(max_digits=14, decimal_places=2)
    totalReceived = serializers.DecimalField(max_digits=14, decimal_places=2)
    pendingAmount = serializers.DecimalField(max_digits=14, decimal_places=2)
    totalExpenses = serializers.DecimalField(max_digits=14, decimal_places=2)
    netProfitLoss = serializers.DecimalField(max_digits=14, decimal_places=2)


class RecentProjectSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    name = serializers.CharField()
    status = serializers.CharField()
    clientName = serializers.CharField()
    createdAt = serializers.DateTimeField()


class RecentQuotationSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    quoteNumber = serializers.CharField()
    version = serializers.IntegerField()
    status = serializers.CharField()
    total = serializers.DecimalField(max_digits=14, decimal_places=2)
    projectName = serializers.CharField()


class InvoiceSummarySerializer(serializers.Serializer):
    """
    Shared shape for both `pendingPayments` and `overdueInvoices` -- the
    two sections have identical fields.
    """

    id = serializers.UUIDField()
    invoiceNumber = serializers.CharField()
    total = serializers.DecimalField(max_digits=14, decimal_places=2)
    dueDate = serializers.DateField(allow_null=True)
    projectName = serializers.CharField()


class RecentExpenseSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    category = serializers.CharField()
    amount = serializers.DecimalField(max_digits=14, decimal_places=2)
    date = serializers.DateField()
    projectName = serializers.CharField()


class UpcomingDeadlineSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    name = serializers.CharField()
    deadline = serializers.DateField()


class ProjectProfitabilitySerializer(serializers.Serializer):
    projectId = serializers.UUIDField()
    projectName = serializers.CharField()
    revenue = serializers.DecimalField(max_digits=14, decimal_places=2)
    expenses = serializers.DecimalField(max_digits=14, decimal_places=2)
    profit = serializers.DecimalField(max_digits=14, decimal_places=2)


class DashboardSerializer(serializers.Serializer):
    """
    Output shape for `GET /reports/dashboard` (BE-048), matching CLAUDE.md's
    Dashboard / Reports section: 8 KPI cards plus 8 "recent" sections.
    `recentActivities` reuses AuditLogSerializer directly (BE-047) rather
    than re-declaring the same shape.
    """

    kpis = DashboardKPISerializer()
    recentProjects = RecentProjectSerializer(many=True)
    recentQuotations = RecentQuotationSerializer(many=True)
    pendingPayments = InvoiceSummarySerializer(many=True)
    overdueInvoices = InvoiceSummarySerializer(many=True)
    recentExpenses = RecentExpenseSerializer(many=True)
    upcomingDeadlines = UpcomingDeadlineSerializer(many=True)
    recentActivities = AuditLogSerializer(many=True)
    projectProfitability = ProjectProfitabilitySerializer(many=True)
