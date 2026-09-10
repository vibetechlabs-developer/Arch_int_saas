from drf_spectacular.utils import extend_schema
from rest_framework import exceptions as drf_exceptions
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.permissions import get_active_membership_for_request
from apps.common.responses import ApiResponse
from apps.dashboard.serializers import DashboardSerializer
from apps.dashboard.services import DashboardService
from apps.projects.permissions import ProjectPermission
from apps.users.permissions import is_platform_admin
from apps.users.services import PermissionService


class DashboardView(APIView):
    """
    `GET /reports/dashboard` (BE-048). Same tenant-resolution/permission
    shape as apps.reports's report views -- no single object to authorize
    against, a company-wide aggregate.
    """

    # `report.view` remains the endpoint-level gate -- PM/Designer-type
    # roles that never held `report.financial_access` must still reach the
    # operational sections. BE-068: the response itself is now split at
    # the source (DashboardService.compute's include_financial flag) so a
    # caller without report.financial_access never receives the genuinely
    # financial fields/sections, closing the exposure this permission
    # split alone didn't (see DashboardSerializer's own docstring).
    permission_classes = [IsAuthenticated, ProjectPermission]
    permission_code = "report.view"

    @extend_schema(
        summary="Dashboard",
        description="KPI cards and recent-activity sections for the tenant's dashboard. Financial fields/sections are only present for a caller holding report.financial_access.",
        responses={status.HTTP_200_OK: DashboardSerializer},
        tags=["Dashboard"],
    )
    def get(self, request: Request) -> Response:
        if is_platform_admin(request):
            company_id = request.query_params.get("companyId")
            if not company_id:
                raise drf_exceptions.ValidationError(
                    {"companyId": ["companyId is required for platform admin dashboard access."]}
                )
            # Platform admin holds the same standing bypass every other
            # permission check in this codebase already grants it --
            # consistent with TenantScopedPermission.has_permission, not a
            # new/separate rule invented here.
            include_financial = True
        else:
            company_id = request.company_id
            membership = get_active_membership_for_request(request)
            include_financial = PermissionService.has_permission(membership, "report.financial_access")

        report = DashboardService.compute(company_id, include_financial=include_financial)
        report["canViewFinancials"] = include_financial

        response_data = DashboardSerializer(report).data
        return ApiResponse.success(
            data=response_data, request_id=getattr(request, "request_id", None)
        )
