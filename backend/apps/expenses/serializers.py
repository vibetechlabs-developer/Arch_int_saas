from rest_framework import serializers

from apps.expenses.models import Expense, ExpenseApprovalStatus
from apps.expenses.selectors import VALID_EXPENSE_ORDER_FIELDS


class ExpenseSerializer(serializers.ModelSerializer):
    """
    Output serializer for Expense, with camelCase JSON fields matching
    every other serializer in this codebase.
    """

    companyId = serializers.UUIDField(source="company_id", read_only=True)
    projectId = serializers.UUIDField(source="project_id", read_only=True)
    projectName = serializers.CharField(source="project.name", read_only=True)
    employeeId = serializers.UUIDField(source="employee_id", read_only=True, allow_null=True)
    employeeName = serializers.CharField(source="employee.name", read_only=True, allow_null=True, default=None)
    amount = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)
    tax = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)
    paymentMethod = serializers.CharField(source="payment_method", read_only=True)
    receiptUrl = serializers.URLField(source="receipt_url", read_only=True)
    addedById = serializers.UUIDField(source="added_by_id", read_only=True, allow_null=True)
    addedByName = serializers.CharField(source="added_by.name", read_only=True, allow_null=True, default=None)
    approvalStatus = serializers.ChoiceField(
        source="approval_status", choices=ExpenseApprovalStatus.choices, read_only=True
    )
    createdAt = serializers.DateTimeField(source="created_at", read_only=True)
    updatedAt = serializers.DateTimeField(source="updated_at", read_only=True)

    class Meta:
        model = Expense
        fields = [
            "id",
            "companyId",
            "projectId",
            "projectName",
            "category",
            "vendor",
            "employeeId",
            "employeeName",
            "amount",
            "tax",
            "date",
            "paymentMethod",
            "receiptUrl",
            "notes",
            "addedById",
            "addedByName",
            "approvalStatus",
            "createdAt",
            "updatedAt",
        ]
        read_only_fields = fields


class ExpenseCreateSerializer(serializers.Serializer):
    """
    Input serializer for `POST /projects/{projectId}/expenses` (BE-044).
    """

    category = serializers.CharField(required=False, allow_blank=True, default="")
    vendor = serializers.CharField(required=False, allow_blank=True, default="")
    employeeId = serializers.UUIDField(source="employee_id", required=False, allow_null=True, default=None)
    amount = serializers.DecimalField(max_digits=14, decimal_places=2, required=True)
    tax = serializers.DecimalField(
        max_digits=14, decimal_places=2, required=False, allow_null=True, default=None
    )
    date = serializers.DateField(required=True)
    paymentMethod = serializers.CharField(
        source="payment_method", required=False, allow_blank=True, default=""
    )
    receiptUrl = serializers.URLField(
        source="receipt_url", required=False, allow_blank=True, default="", max_length=500
    )
    notes = serializers.CharField(required=False, allow_blank=True, default="")


class ExpenseUpdateSerializer(serializers.Serializer):
    """
    Input serializer for `PATCH /expenses/{expenseId}` (BE-044, draft
    only -- added for CRUD consistency, not itself documented in
    Finance_API.md). Every field is optional with no non-None default,
    the same "omission means unchanged" contract
    QuotationReviseSerializer/InvoiceUpdateSerializer established.
    `employeeId` allows explicit `null` to clear the employee.
    """

    category = serializers.CharField(required=False, allow_blank=True, default=None, allow_null=True)
    vendor = serializers.CharField(required=False, allow_blank=True, default=None, allow_null=True)
    employeeId = serializers.UUIDField(
        source="employee_id", required=False, allow_null=True, default="unset"
    )
    amount = serializers.DecimalField(
        max_digits=14, decimal_places=2, required=False, allow_null=True, default=None
    )
    tax = serializers.DecimalField(
        max_digits=14, decimal_places=2, required=False, allow_null=True, default=None
    )
    date = serializers.DateField(required=False, allow_null=True, default=None)
    paymentMethod = serializers.CharField(
        source="payment_method", required=False, allow_blank=True, default=None, allow_null=True
    )
    receiptUrl = serializers.URLField(
        source="receipt_url", required=False, allow_blank=True, default=None, allow_null=True, max_length=500
    )
    notes = serializers.CharField(required=False, allow_blank=True, default=None, allow_null=True)


class ExpenseListQuerySerializer(serializers.Serializer):
    """
    Validates GET /projects/{projectId}/expenses query params (BE-044):
    category/vendor/employee/date filters, matching Finance_API.md's
    documented set exactly, plus approval_status and ordering.
    """

    category = serializers.CharField(required=False, default=None, allow_null=True, allow_blank=True)
    vendor = serializers.CharField(required=False, default=None, allow_null=True, allow_blank=True)
    employee = serializers.UUIDField(
        source="employee_id", required=False, default=None, allow_null=True
    )
    approvalStatus = serializers.ChoiceField(
        source="approval_status",
        choices=ExpenseApprovalStatus.choices,
        required=False,
        default=None,
        allow_null=True,
    )
    dateFrom = serializers.DateField(source="date_from", required=False, default=None, allow_null=True)
    dateTo = serializers.DateField(source="date_to", required=False, default=None, allow_null=True)
    ordering = serializers.ChoiceField(
        choices=sorted(VALID_EXPENSE_ORDER_FIELDS), required=False, default="-date"
    )
