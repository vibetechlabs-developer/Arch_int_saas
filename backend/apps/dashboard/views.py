from drf_spectacular.utils import extend_schema
from rest_framework import exceptions as drf_exceptions
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.responses import ApiResponse
from apps.dashboard.serializers import DashboardSerializer
from apps.dashboard.services import DashboardService
from apps.projects.permissions import ProjectPermission
from apps.users.permissions import is_platform_admin


class DashboardView(APIView):
    """
    `GET /reports/dashboard` (BE-048). Same tenant-resolution/permission
    shape as apps.reports's report views -- no single object to authorize
    against, a company-wide aggregate.
    """

    permission_classes = [IsAuthenticated, ProjectPermission]

    @extend_schema(
        summary="Dashboard",
        description="KPI cards and recent-activity sections for the tenant's dashboard.",
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
        else:
            company_id = request.company_id

        report = DashboardService.compute(company_id)

        response_data = DashboardSerializer(report).data
        return ApiResponse.success(
            data=response_data, request_id=getattr(request, "request_id", None)
        )
