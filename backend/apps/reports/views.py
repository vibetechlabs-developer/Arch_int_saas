from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import exceptions as drf_exceptions
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.responses import ApiResponse
from apps.projects.permissions import ProjectPermission
from apps.reports.serializers import (
    ExpenseReportSerializer,
    FinanceReportQuerySerializer,
    FinanceReportSerializer,
)
from apps.reports.services import ExpenseReportService, FinanceReportService
from apps.users.permissions import is_platform_admin

REPORT_QUERY_PARAMETERS = [
    OpenApiParameter(name="projectId", description="Scope to one project.", required=False, type=str),
    OpenApiParameter(name="dateFrom", required=False, type=str),
    OpenApiParameter(name="dateTo", required=False, type=str),
]


def _resolve_target_company_id(request: Request) -> str:
    """
    Shared company-tenant resolution for both report views -- mirrors
    every list endpoint's `resolve_create_target_company_id` pattern
    (e.g. ProductCategoryService's): a company user always reports on
    their own resolved `request.company_id`; a platform admin must supply
    `?companyId=` explicitly, since they have no single resolved tenant.
    """
    if is_platform_admin(request):
        company_id = request.query_params.get("companyId")
        if not company_id:
            raise drf_exceptions.ValidationError(
                {"companyId": ["companyId is required for platform admin report access."]}
            )
        return company_id

    return request.company_id


class FinanceReportView(APIView):
    """
    `GET /reports/finance` (BE-045). No single object to authorize
    against (a company-wide aggregate, not one entity) -- relies solely
    on ProjectPermission.has_permission (authenticated + resolved tenant),
    the same "no check_object_permissions call needed" shape a plain list
    endpoint has.
    """

    permission_classes = [IsAuthenticated, ProjectPermission]
    permission_code = "report.financial_access"

    @extend_schema(
        summary="Finance Report",
        description="Revenue, received, receivables, outstanding, expenses, and profit/loss for the tenant.",
        parameters=REPORT_QUERY_PARAMETERS,
        responses={status.HTTP_200_OK: FinanceReportSerializer},
        tags=["Reports"],
    )
    def get(self, request: Request) -> Response:
        company_id = _resolve_target_company_id(request)

        query = FinanceReportQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        validated = query.validated_data

        report = FinanceReportService.compute(
            company_id=company_id,
            project_id=validated["project_id"],
            date_from=validated["date_from"],
            date_to=validated["date_to"],
        )

        response_data = FinanceReportSerializer(report).data
        return ApiResponse.success(
            data=response_data, request_id=getattr(request, "request_id", None)
        )


class ExpenseReportView(APIView):
    """
    `GET /reports/expenses` (BE-045). Same tenant-resolution/permission
    shape as FinanceReportView.
    """

    permission_classes = [IsAuthenticated, ProjectPermission]
    permission_code = "report.financial_access"

    @extend_schema(
        summary="Expense Report",
        description="Expense breakdowns by category, project, vendor, employee, and date.",
        parameters=REPORT_QUERY_PARAMETERS,
        responses={status.HTTP_200_OK: ExpenseReportSerializer},
        tags=["Reports"],
    )
    def get(self, request: Request) -> Response:
        company_id = _resolve_target_company_id(request)

        query = FinanceReportQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        validated = query.validated_data

        report = ExpenseReportService.compute(
            company_id=company_id,
            project_id=validated["project_id"],
            date_from=validated["date_from"],
            date_to=validated["date_to"],
        )

        response_data = ExpenseReportSerializer(report).data
        return ApiResponse.success(
            data=response_data, request_id=getattr(request, "request_id", None)
        )
