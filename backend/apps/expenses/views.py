from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.responses import ApiResponse
from apps.common.views import ObjectPermission404Mixin
from apps.expenses.serializers import (
    ExpenseCreateSerializer,
    ExpenseListQuerySerializer,
    ExpenseSerializer,
    ExpenseUpdateSerializer,
)
from apps.expenses.services import ExpenseService
from apps.projects.permissions import ProjectPermission
from apps.projects.services import ProjectService


class ExpenseListCreateView(ObjectPermission404Mixin, APIView):
    """
    `GET`/`POST /projects/{projectId}/expenses` (BE-044). Reuses
    ProjectPermission directly, matching every nested-under-Project
    resource in this codebase (Expense has its own real `company`
    column). Unpaginated -- same precedent as Quotation/Invoice lists.
    """

    permission_classes = [IsAuthenticated, ProjectPermission]
    permission_code_map = {"get": "expense.view", "post": "expense.create"}

    @extend_schema(
        summary="List Project Expenses",
        description="List a project's expenses, filterable by category/vendor/employee/date/approvalStatus.",
        parameters=[
            OpenApiParameter(name="category", required=False, type=str),
            OpenApiParameter(name="vendor", required=False, type=str),
            OpenApiParameter(name="employee", description="Filter by employee UUID.", required=False, type=str),
            OpenApiParameter(name="approvalStatus", required=False, type=str),
            OpenApiParameter(name="dateFrom", required=False, type=str),
            OpenApiParameter(name="dateTo", required=False, type=str),
            OpenApiParameter(name="ordering", required=False, type=str),
        ],
        responses={status.HTTP_200_OK: ExpenseSerializer(many=True)},
        tags=["Expenses"],
    )
    def get(self, request: Request, project_id: str = None) -> Response:
        project = ProjectService.get_project_by_id(project_id)
        self.check_object_permissions(request, project)

        query = ExpenseListQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        validated = query.validated_data

        queryset = ExpenseService.list_expenses_for_project(
            project,
            category=validated["category"],
            vendor=validated["vendor"],
            employee_id=validated["employee_id"],
            approval_status=validated["approval_status"],
            date_from=validated["date_from"],
            date_to=validated["date_to"],
            ordering=validated["ordering"],
        )

        serializer = ExpenseSerializer(queryset, many=True)
        return ApiResponse.success(
            data=serializer.data, request_id=getattr(request, "request_id", None)
        )

    @extend_schema(
        summary="Create Expense",
        description="Submit a new expense (draft) for a project.",
        request=ExpenseCreateSerializer,
        responses={status.HTTP_201_CREATED: ExpenseSerializer},
        tags=["Expenses"],
    )
    def post(self, request: Request, project_id: str = None) -> Response:
        project = ProjectService.get_project_by_id(project_id)
        self.check_object_permissions(request, project)

        serializer = ExpenseCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated = serializer.validated_data

        expense = ExpenseService.create_expense(
            project=project,
            category=validated.get("category", ""),
            vendor=validated.get("vendor", ""),
            employee_id=validated.get("employee_id"),
            amount=validated["amount"],
            tax=validated.get("tax"),
            date=validated["date"],
            payment_method=validated.get("payment_method", ""),
            receipt_url=validated.get("receipt_url", ""),
            notes=validated.get("notes", ""),
            actor_user=request.user,
            request=request,
        )

        response_data = ExpenseSerializer(expense).data
        return ApiResponse.created(
            data=response_data, request_id=getattr(request, "request_id", None)
        )


class ExpenseDetailView(ObjectPermission404Mixin, APIView):
    """
    `GET`/`PATCH`/`DELETE /expenses/{expenseId}` (BE-044). PATCH/DELETE
    are draft-only (added for CRUD consistency -- see
    ExpenseService.update_expense/soft_delete_expense's docstrings; not
    themselves documented in Finance_API.md).
    """

    permission_classes = [IsAuthenticated, ProjectPermission]
    permission_code_map = {"get": "expense.view", "patch": "expense.edit", "delete": "expense.delete"}

    @extend_schema(
        summary="Get Expense",
        responses={status.HTTP_200_OK: ExpenseSerializer},
        tags=["Expenses"],
    )
    def get(self, request: Request, expense_id: str = None) -> Response:
        expense = ExpenseService.get_expense_by_id(expense_id)
        self.check_object_permissions(request, expense)

        response_data = ExpenseSerializer(expense).data
        return ApiResponse.success(
            data=response_data, request_id=getattr(request, "request_id", None)
        )

    @extend_schema(
        summary="Update Expense",
        description="Edit a draft expense. Any field omitted from the request is left unchanged.",
        request=ExpenseUpdateSerializer,
        responses={status.HTTP_200_OK: ExpenseSerializer},
        tags=["Expenses"],
    )
    def patch(self, request: Request, expense_id: str = None) -> Response:
        expense = ExpenseService.get_expense_by_id(expense_id)
        self.check_object_permissions(request, expense)

        # Deliberately NOT partial=True: ExpenseUpdateSerializer's
        # `employeeId` field relies on its own declared `default="unset"`
        # sentinel to distinguish "omitted" from "explicit null" -- DRF's
        # partial=True mode skips a field's own default entirely for any
        # key absent from the request body, which would break that
        # distinction. Every field already has `required=False`, so
        # nothing here is actually mandatory.
        serializer = ExpenseUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated = serializer.validated_data

        updated = ExpenseService.update_expense(
            expense,
            category=validated.get("category"),
            vendor=validated.get("vendor"),
            employee_id=validated.get("employee_id", "unset"),
            amount=validated.get("amount"),
            tax=validated.get("tax"),
            date=validated.get("date"),
            payment_method=validated.get("payment_method"),
            receipt_url=validated.get("receipt_url"),
            notes=validated.get("notes"),
            actor_user=request.user,
            request=request,
        )

        response_data = ExpenseSerializer(updated).data
        return ApiResponse.success(
            data=response_data, request_id=getattr(request, "request_id", None)
        )

    @extend_schema(
        summary="Delete Expense",
        description="Soft-delete a draft expense.",
        responses={status.HTTP_200_OK: None},
        tags=["Expenses"],
    )
    def delete(self, request: Request, expense_id: str = None) -> Response:
        expense = ExpenseService.get_expense_by_id(expense_id)
        self.check_object_permissions(request, expense)

        ExpenseService.soft_delete_expense(expense, actor_user=request.user, request=request)
        return ApiResponse.success(
            data={"message": "Expense deleted successfully."},
            request_id=getattr(request, "request_id", None),
        )


class ExpenseSubmitView(ObjectPermission404Mixin, APIView):
    """`POST /expenses/{expenseId}/submit` (BE-044): draft -> submitted."""

    # BE-054 §5: Backend-Lead-approved provisional mapping (submit ->
    # expense.edit) — see RBAC_Enforcement_Matrix.md.
    permission_classes = [IsAuthenticated, ProjectPermission]
    permission_code = "expense.edit"

    @extend_schema(request=None, responses={status.HTTP_200_OK: ExpenseSerializer}, tags=["Expenses"])
    def post(self, request: Request, expense_id: str = None) -> Response:
        expense = ExpenseService.get_expense_by_id(expense_id)
        self.check_object_permissions(request, expense)

        updated = ExpenseService.submit_expense(expense, actor_user=request.user, request=request)
        response_data = ExpenseSerializer(updated).data
        return ApiResponse.success(
            data=response_data, request_id=getattr(request, "request_id", None)
        )


class ExpenseApproveView(ObjectPermission404Mixin, APIView):
    """`POST /expenses/{expenseId}/approve` (BE-044): submitted -> approved."""

    permission_classes = [IsAuthenticated, ProjectPermission]
    permission_code = "expense.approve"

    @extend_schema(request=None, responses={status.HTTP_200_OK: ExpenseSerializer}, tags=["Expenses"])
    def post(self, request: Request, expense_id: str = None) -> Response:
        expense = ExpenseService.get_expense_by_id(expense_id)
        self.check_object_permissions(request, expense)

        updated = ExpenseService.approve_expense(expense, actor_user=request.user, request=request)
        response_data = ExpenseSerializer(updated).data
        return ApiResponse.success(
            data=response_data, request_id=getattr(request, "request_id", None)
        )


class ExpenseMarkPaidView(ObjectPermission404Mixin, APIView):
    """`POST /expenses/{expenseId}/mark-paid` (BE-044): approved -> paid."""

    # BE-054 §5: Backend-Lead-approved provisional mapping (mark-paid ->
    # expense.approve, same final-approver authority) — see
    # RBAC_Enforcement_Matrix.md.
    permission_classes = [IsAuthenticated, ProjectPermission]
    permission_code = "expense.approve"

    @extend_schema(request=None, responses={status.HTTP_200_OK: ExpenseSerializer}, tags=["Expenses"])
    def post(self, request: Request, expense_id: str = None) -> Response:
        expense = ExpenseService.get_expense_by_id(expense_id)
        self.check_object_permissions(request, expense)

        updated = ExpenseService.mark_paid_expense(expense, actor_user=request.user, request=request)
        response_data = ExpenseSerializer(updated).data
        return ApiResponse.success(
            data=response_data, request_id=getattr(request, "request_id", None)
        )
