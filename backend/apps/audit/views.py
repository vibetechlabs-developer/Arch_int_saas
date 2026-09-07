from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import exceptions as drf_exceptions
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.audit.serializers import ActivityLogListQuerySerializer, AuditLogSerializer
from apps.audit.services import ActivityLogService
from apps.common.pagination import StandardPagination
from apps.common.responses import ApiResponse
from apps.projects.permissions import ProjectPermission
from apps.users.permissions import is_platform_admin


def _resolve_target_company_id(request: Request) -> str:
    """
    Same tenant-resolution shape as apps.reports.views's identical helper
    -- a company user always sees their own resolved `request.company_id`;
    a platform admin must supply `?companyId=` explicitly. Duplicated
    rather than imported (three lines, and importing from apps.reports
    into apps.audit would be an odd dependency direction for a helper
    this small).
    """
    if is_platform_admin(request):
        company_id = request.query_params.get("companyId")
        if not company_id:
            raise drf_exceptions.ValidationError(
                {"companyId": ["companyId is required for platform admin activity log access."]}
            )
        return company_id

    return request.company_id


class ActivityLogListView(APIView):
    """
    `GET /activity-logs` (BE-047) -- tenant-wide, so paginated (unlike
    Quotation/Invoice/Expense's nested-under-Project lists, this is
    exactly the "unbounded tenant-wide collection" CompanyViewSet/
    ProductViewSet's own pagination precedent covers). No single object
    to authorize against -- relies solely on ProjectPermission's
    `has_permission` (authenticated + resolved tenant), the same shape
    apps.reports's views use.
    """

    permission_classes = [IsAuthenticated, ProjectPermission]
    pagination_class = StandardPagination
    permission_code = "audit.view"

    @extend_schema(
        summary="List Activity Logs",
        description="Tenant-wide activity feed, filterable by entityType/entityId/action/actorUserId/date range.",
        parameters=[
            OpenApiParameter(name="entityType", required=False, type=str),
            OpenApiParameter(name="entityId", required=False, type=str),
            OpenApiParameter(name="action", required=False, type=str),
            OpenApiParameter(name="actorUserId", required=False, type=str),
            OpenApiParameter(name="dateFrom", required=False, type=str),
            OpenApiParameter(name="dateTo", required=False, type=str),
            OpenApiParameter(name="ordering", required=False, type=str),
        ],
        responses={status.HTTP_200_OK: AuditLogSerializer(many=True)},
        tags=["Activity Logs"],
    )
    def get(self, request: Request) -> Response:
        company_id = _resolve_target_company_id(request)

        query = ActivityLogListQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        validated = query.validated_data

        queryset = ActivityLogService.list_activity_for_company(
            company_id=company_id,
            entity_type=validated["entity_type"],
            entity_id=validated["entity_id"],
            action=validated["action"],
            actor_user_id=validated["actor_user_id"],
            date_from=validated["date_from"],
            date_to=validated["date_to"],
            ordering=validated["ordering"],
        )

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset, request, view=self)
        request_id = getattr(request, "request_id", None)

        if page is not None:
            serializer = AuditLogSerializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)

        serializer = AuditLogSerializer(queryset, many=True)
        return ApiResponse.success(data=serializer.data, request_id=request_id)
