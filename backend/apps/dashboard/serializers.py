from rest_framework import serializers

from apps.audit.serializers import AuditLogSerializer


class DashboardKPISerializer(serializers.Serializer):
    """
    BE-068: the five money fields are `required=False` with no `default` --
    when the source dict omits one of these keys (DashboardService.compute
    never puts them there at all for a caller without
    `report.financial_access`), DRF's Field.get_attribute raises SkipField
    internally and the key is left out of the serialized output entirely.
    Not a null, not a zero -- genuinely absent.
    """

    totalProjects = serializers.IntegerField()
    activeProjects = serializers.IntegerField()
    totalQuotations = serializers.IntegerField()
    totalBilledRevenue = serializers.DecimalField(max_digits=14, decimal_places=2, required=False)
    totalReceived = serializers.DecimalField(max_digits=14, decimal_places=2, required=False)
    pendingAmount = serializers.DecimalField(max_digits=14, decimal_places=2, required=False)
    totalExpenses = serializers.DecimalField(max_digits=14, decimal_places=2, required=False)
    netProfitLoss = serializers.DecimalField(max_digits=14, decimal_places=2, required=False)


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

    BE-068: `pendingPayments`/`overdueInvoices`/`recentExpenses`/
    `projectProfitability` are genuinely financial sections (invoice
    totals, expense amounts, revenue/profit) -- `required=False` so they
    can be omitted entirely (same SkipField mechanism as
    DashboardKPISerializer's money fields) for a caller without
    `report.financial_access`. `recentActivities` is also gated despite
    being conceptually operational -- confirmed by direct testing that
    its `beforeState`/`afterState` snapshots leak real financial figures
    whenever the audited entity is an invoice/payment (see
    DashboardService.compute's docstring for why the whole section is
    gated rather than filtered per-entry). `recentProjects`/
    `recentQuotations`/`upcomingDeadlines` carry no financial figures and
    stay unconditional. `canViewFinancials` accompanies the omission as a
    UX convenience for the frontend -- it never substitutes for it; the
    financial keys are still genuinely absent from the payload regardless
    of this flag's value.
    """

    canViewFinancials = serializers.BooleanField()
    kpis = DashboardKPISerializer()
    recentProjects = RecentProjectSerializer(many=True)
    recentQuotations = RecentQuotationSerializer(many=True)
    pendingPayments = InvoiceSummarySerializer(many=True, required=False)
    overdueInvoices = InvoiceSummarySerializer(many=True, required=False)
    recentExpenses = RecentExpenseSerializer(many=True, required=False)
    upcomingDeadlines = UpcomingDeadlineSerializer(many=True)
    recentActivities = AuditLogSerializer(many=True, required=False)
    projectProfitability = ProjectProfitabilitySerializer(many=True, required=False)
