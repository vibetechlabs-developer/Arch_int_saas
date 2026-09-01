from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.responses import ApiResponse
from apps.common.views import ObjectPermission404Mixin
from apps.projects.permissions import ProjectPermission
from apps.projects.services import ProjectService
from apps.quotations.serializers import (
    QuotationCreateSerializer,
    QuotationListQuerySerializer,
    QuotationReviseSerializer,
    QuotationSerializer,
)
from apps.quotations.services import QuotationService


class QuotationListCreateView(ObjectPermission404Mixin, APIView):
    """
    `GET`/`POST /projects/{projectId}/quotations` (BE-039). Reuses
    ProjectPermission directly, the same pattern every nested-under-Project
    resource in this codebase uses (BOQSectionListCreateView,
    ProjectTeamView) -- Quotation has its own real `company` column
    (unlike BOQSection/BOQItem), so ProjectPermission's generic
    `obj.company_id` check works against a Quotation object unchanged too.
    Unpaginated, matching ProjectTeamView's precedent for a nested list
    that's naturally small (a handful of quotation versions per project,
    not an unbounded tenant-wide collection).
    """

    permission_classes = [IsAuthenticated, ProjectPermission]

    @extend_schema(
        summary="List Project Quotations",
        description="List every version of every quotation for a project.",
        parameters=[
            OpenApiParameter(
                name="ordering",
                description="Ordering field (e.g. version, -version, created_at, -created_at).",
                required=False,
                type=str,
            ),
        ],
        responses={status.HTTP_200_OK: QuotationSerializer(many=True)},
        tags=["Quotations"],
    )
    def get(self, request: Request, project_id: str = None) -> Response:
        project = ProjectService.get_project_by_id(project_id)
        self.check_object_permissions(request, project)

        query = QuotationListQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)

        queryset = QuotationService.list_quotations_for_project(
            project, ordering=query.validated_data["ordering"]
        )

        serializer = QuotationSerializer(queryset, many=True)
        return ApiResponse.success(
            data=serializer.data, request_id=getattr(request, "request_id", None)
        )

    @extend_schema(
        summary="Create Quotation",
        description="Create a quotation for a project, either from its BOQ (omit `items`) or manually (supply `items`).",
        request=QuotationCreateSerializer,
        responses={status.HTTP_201_CREATED: QuotationSerializer},
        tags=["Quotations"],
    )
    def post(self, request: Request, project_id: str = None) -> Response:
        project = ProjectService.get_project_by_id(project_id)
        self.check_object_permissions(request, project)

        serializer = QuotationCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated = serializer.validated_data

        quotation = QuotationService.create_quotation(
            project=project,
            items=validated.get("items"),
            discount=validated.get("discount"),
            tax=validated.get("tax"),
            terms=validated.get("terms", ""),
            payment_schedule=validated.get("payment_schedule"),
            valid_until=validated.get("valid_until"),
            notes=validated.get("notes", ""),
            actor_user=request.user,
            request=request,
        )

        response_data = QuotationSerializer(quotation).data
        return ApiResponse.created(
            data=response_data, request_id=getattr(request, "request_id", None)
        )


class QuotationDetailView(ObjectPermission404Mixin, APIView):
    """
    `GET /quotations/{quotationId}` (BE-039). Read-only, deliberately --
    no PATCH/DELETE exists for Quotation (Backend Lead decision, Sprint 5
    planning): a versioned commercial document's content should only ever
    change through QuotationService.revise_quotation (BE-040), which
    creates a new version rather than mutating a sent one, so a generic
    edit endpoint here would undermine the whole versioning model. This is
    a deliberate exception to the "add CRUD for consistency" precedent
    (BE-031 Category/Subcategory DELETE, BOQSection PATCH/DELETE) rather
    than an oversight.
    """

    permission_classes = [IsAuthenticated, ProjectPermission]

    @extend_schema(
        summary="Get Quotation",
        description="Get one quotation version's full detail, including its items.",
        responses={status.HTTP_200_OK: QuotationSerializer},
        tags=["Quotations"],
    )
    def get(self, request: Request, quotation_id: str = None) -> Response:
        quotation = QuotationService.get_quotation_by_id(quotation_id)
        self.check_object_permissions(request, quotation)

        response_data = QuotationSerializer(quotation).data
        return ApiResponse.success(
            data=response_data, request_id=getattr(request, "request_id", None)
        )


class QuotationReviseView(ObjectPermission404Mixin, APIView):
    """
    `POST /quotations/{quotationId}/revise` (BE-040). Creates a new
    version rather than mutating `quotationId` -- see
    QuotationService.revise_quotation's docstring for the clone-then-
    partial-override semantics and the "only the latest version" guard.
    """

    permission_classes = [IsAuthenticated, ProjectPermission]

    @extend_schema(
        summary="Revise Quotation",
        description="Create a new version of a quotation. Any field omitted from the request carries over from the source version unchanged.",
        request=QuotationReviseSerializer,
        responses={status.HTTP_201_CREATED: QuotationSerializer},
        tags=["Quotations"],
    )
    def post(self, request: Request, quotation_id: str = None) -> Response:
        quotation = QuotationService.get_quotation_by_id(quotation_id)
        self.check_object_permissions(request, quotation)

        serializer = QuotationReviseSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated = serializer.validated_data

        new_version = QuotationService.revise_quotation(
            quotation=quotation,
            items=validated.get("items"),
            discount=validated.get("discount"),
            tax=validated.get("tax"),
            terms=validated.get("terms"),
            payment_schedule=validated.get("payment_schedule"),
            valid_until=validated.get("valid_until"),
            notes=validated.get("notes"),
            actor_user=request.user,
            request=request,
        )

        response_data = QuotationSerializer(new_version).data
        return ApiResponse.created(
            data=response_data, request_id=getattr(request, "request_id", None)
        )


class QuotationSendView(ObjectPermission404Mixin, APIView):
    """
    `POST /quotations/{quotationId}/send` (BE-041): draft -> sent.
    """

    permission_classes = [IsAuthenticated, ProjectPermission]

    @extend_schema(
        summary="Send Quotation",
        description="Mark a draft quotation as sent to the client.",
        request=None,
        responses={status.HTTP_200_OK: QuotationSerializer},
        tags=["Quotations"],
    )
    def post(self, request: Request, quotation_id: str = None) -> Response:
        quotation = QuotationService.get_quotation_by_id(quotation_id)
        self.check_object_permissions(request, quotation)

        updated = QuotationService.send_quotation(quotation, actor_user=request.user, request=request)

        response_data = QuotationSerializer(updated).data
        return ApiResponse.success(
            data=response_data, request_id=getattr(request, "request_id", None)
        )


class QuotationApproveView(ObjectPermission404Mixin, APIView):
    """
    `POST /quotations/{quotationId}/approve` (BE-041): sent -> approved.
    """

    permission_classes = [IsAuthenticated, ProjectPermission]

    @extend_schema(
        summary="Approve Quotation",
        description="Record the client's approval of a sent quotation.",
        request=None,
        responses={status.HTTP_200_OK: QuotationSerializer},
        tags=["Quotations"],
    )
    def post(self, request: Request, quotation_id: str = None) -> Response:
        quotation = QuotationService.get_quotation_by_id(quotation_id)
        self.check_object_permissions(request, quotation)

        updated = QuotationService.approve_quotation(quotation, actor_user=request.user, request=request)

        response_data = QuotationSerializer(updated).data
        return ApiResponse.success(
            data=response_data, request_id=getattr(request, "request_id", None)
        )


class QuotationRejectView(ObjectPermission404Mixin, APIView):
    """
    `POST /quotations/{quotationId}/reject` (BE-041): sent -> rejected.
    Always the terminal `rejected` status -- see
    QuotationService.reject_quotation's docstring for why no
    `revision_requested` outcome is offered here.
    """

    permission_classes = [IsAuthenticated, ProjectPermission]

    @extend_schema(
        summary="Reject Quotation",
        description="Record the client's rejection of a sent quotation. To offer a revision instead, call /revise directly.",
        request=None,
        responses={status.HTTP_200_OK: QuotationSerializer},
        tags=["Quotations"],
    )
    def post(self, request: Request, quotation_id: str = None) -> Response:
        quotation = QuotationService.get_quotation_by_id(quotation_id)
        self.check_object_permissions(request, quotation)

        updated = QuotationService.reject_quotation(quotation, actor_user=request.user, request=request)

        response_data = QuotationSerializer(updated).data
        return ApiResponse.success(
            data=response_data, request_id=getattr(request, "request_id", None)
        )
