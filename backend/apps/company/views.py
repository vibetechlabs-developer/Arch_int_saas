from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import status, viewsets
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.pagination import StandardPagination
from apps.common.responses import ApiResponse
from apps.common.views import ObjectPermission404Mixin
from apps.company.models import Company
from apps.company.permissions import IsPlatformAdminOrCompanyAccess, is_platform_admin
from apps.company.serializers import (
    CompanyCreateResponseSerializer,
    CompanyCreateSerializer,
    CompanyListQuerySerializer,
    CompanyLogoUploadSerializer,
    CompanyOwnerSerializer,
    CompanySerializer,
    CompanyUpdateSerializer,
    SetOwnerPasswordResponseSerializer,
    SetOwnerPasswordSerializer,
)
from apps.company.services import CompanyService


@extend_schema_view(
    list=extend_schema(
        summary="List Companies",
        description="List all active tenant companies (Platform Admin only).",
        responses={status.HTTP_200_OK: CompanySerializer(many=True)},
        tags=["Company"],
    ),
    create=extend_schema(
        summary="Create Company",
        description=(
            "Create a new tenant company (Platform Admin only). Optionally supply "
            "ownerEmail/ownerName together to also grant the new company's Owner role "
            "to that email (BE-071's Add User flow) -- the response then includes "
            "an `owner` object; omitted entirely when no owner was requested."
        ),
        request=CompanyCreateSerializer,
        responses={status.HTTP_201_CREATED: CompanyCreateResponseSerializer},
        tags=["Company"],
    ),
    retrieve=extend_schema(
        summary="Retrieve Company",
        description="Retrieve company details by UUID.",
        responses={status.HTTP_200_OK: CompanySerializer},
        tags=["Company"],
    ),
    partial_update=extend_schema(
        summary="Update Company",
        description="Partially update company details by UUID.",
        request=CompanyUpdateSerializer,
        responses={status.HTTP_200_OK: CompanySerializer},
        tags=["Company"],
    ),
    destroy=extend_schema(
        summary="Delete Company",
        description="Soft-delete a company tenant by UUID (Platform Admin only).",
        responses={status.HTTP_200_OK: CompanySerializer},
        tags=["Company"],
    ),
)
class CompanyViewSet(ObjectPermission404Mixin, viewsets.GenericViewSet):
    """
    ViewSet for Company tenant CRUD operations.
    Enforces standard ApiResponse envelopes and permission boundaries.
    """

    permission_classes = [IsAuthenticated, IsPlatformAdminOrCompanyAccess]
    pagination_class = StandardPagination
    serializer_class = CompanySerializer
    # Every action below is fully overridden and goes through CompanyService
    # rather than self.get_queryset()/self.get_object() — this attribute is
    # inert at runtime and exists solely so drf-spectacular (BE-016) can
    # resolve the response model for schema generation.
    queryset = Company.objects.none()
    # BE-054 §7: Admin was corrected to hold both of these (see
    # permission_catalog.py's DEFAULT_ROLE_PERMISSIONS reconciliation).
    # list/create/destroy stay Platform-Admin-exclusive (no code needed —
    # IsPlatformAdminOrCompanyAccess.has_permission denies non-admins
    # outright before this map is even consulted).
    permission_code_map = {
        "retrieve": "company.view",
        "partial_update": "company.manage",
        "update": "company.manage",
    }

    def list(self, request: Request) -> Response:
        """
        List companies with status filter and search query.
        """
        query = CompanyListQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)

        queryset = CompanyService.list_companies(
            status=query.validated_data["status"],
            search=query.validated_data["search"] or None,
            ordering=query.validated_data["ordering"],
        )

        page = self.paginate_queryset(queryset)
        request_id = getattr(request, "request_id", None)

        if page is not None:
            serializer = CompanySerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = CompanySerializer(queryset, many=True)
        return ApiResponse.success(data=serializer.data, request_id=request_id)

    def create(self, request: Request) -> Response:
        """
        Create a new tenant company. Optionally, when `ownerEmail`/
        `ownerName` are supplied, also grants the new company's Owner
        role to that email (see CompanyService.create_company's
        docstring) -- the response then carries `owner: {userCreated,
        activationRequired}` alongside the usual company fields;
        `owner` is omitted entirely when no owner was requested, so an
        existing caller that never sends these fields sees no shape
        change at all.
        """
        serializer = CompanyCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        company, owner_result = CompanyService.create_company(
            **serializer.validated_data,
            actor_user=request.user,
            request=request,
        )
        response_data = CompanySerializer(company).data
        if owner_result is not None:
            response_data["owner"] = owner_result
        request_id = getattr(request, "request_id", None)

        return ApiResponse.created(data=response_data, request_id=request_id)

    def retrieve(self, request: Request, pk: str = None) -> Response:
        """
        Retrieve details of a single company.
        """
        company = CompanyService.get_company_by_id(pk)
        self.check_object_permissions(request, company)

        response_data = CompanySerializer(company).data
        request_id = getattr(request, "request_id", None)

        return ApiResponse.success(data=response_data, request_id=request_id)

    def partial_update(self, request: Request, pk: str = None) -> Response:
        """
        Partially update an existing company.
        """
        company = CompanyService.get_company_by_id(pk)
        self.check_object_permissions(request, company)

        serializer = CompanyUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        updated_company = CompanyService.update_company(
            company_id=pk,
            validated_data=serializer.validated_data,
            is_platform_admin=is_platform_admin(request),
            actor_user=request.user,
            request=request,
        )
        response_data = CompanySerializer(updated_company).data
        request_id = getattr(request, "request_id", None)

        return ApiResponse.success(data=response_data, request_id=request_id)

    def update(self, request: Request, pk: str = None) -> Response:
        """
        Full update forwards to partial_update logic.
        """
        return self.partial_update(request, pk=pk)

    def destroy(self, request: Request, pk: str = None) -> Response:
        """
        Soft-delete a company.
        """
        company = CompanyService.get_company_by_id(pk)
        self.check_object_permissions(request, company)

        CompanyService.soft_delete_company(pk, actor_user=request.user, request=request)
        request_id = getattr(request, "request_id", None)

        return ApiResponse.success(
            data={"message": "Company deleted successfully."},
            request_id=request_id,
        )

    @extend_schema(
        summary="Get Company Owner",
        description=(
            "Who this company's Owner is (Platform Admin only) -- including whether they've ever "
            "completed account setup, so an admin knows before reaching for Set Owner Password."
        ),
        responses={status.HTTP_200_OK: CompanyOwnerSerializer},
        tags=["Company"],
    )
    def owner(self, request: Request, pk: str = None) -> Response:
        company = CompanyService.get_company_by_id(pk)
        self.check_object_permissions(request, company)

        result = CompanyService.get_owner(pk)
        request_id = getattr(request, "request_id", None)
        return ApiResponse.success(data=CompanyOwnerSerializer(result).data, request_id=request_id)

    @extend_schema(
        summary="Set Company Owner Password",
        description=(
            "Directly set this company's Owner's password (Platform Admin only), bypassing "
            "the normal email-token activation flow -- for onboarding an Owner in an "
            "environment where the account-setup email isn't reachable (e.g. dev's console "
            "email backend). Blacklists the Owner's existing refresh tokens."
        ),
        request=SetOwnerPasswordSerializer,
        responses={status.HTTP_200_OK: SetOwnerPasswordResponseSerializer},
        tags=["Company"],
    )
    def set_owner_password(self, request: Request, pk: str = None) -> Response:
        company = CompanyService.get_company_by_id(pk)
        self.check_object_permissions(request, company)

        serializer = SetOwnerPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        result = CompanyService.set_owner_password(
            company_id=pk,
            new_password=serializer.validated_data["new_password"],
            actor_user=request.user,
            request=request,
        )
        request_id = getattr(request, "request_id", None)
        return ApiResponse.success(
            data=SetOwnerPasswordResponseSerializer(result).data,
            request_id=request_id,
        )


class CompanyLogoUploadView(ObjectPermission404Mixin, APIView):
    """
    `POST /companies/{id}/logo/upload` (BE-078). Reuses
    `IsPlatformAdminOrCompanyAccess` directly -- its object-level check
    (tenant match against `request.company_id`) and permission-code
    resolution (`company.manage`, the same code
    `CompanyViewSet.partial_update` already requires) apply unchanged;
    `action = "partial_update"` is a deliberate fixed class attribute (not
    DRF's own ViewSet-assigned one, since this is a plain APIView) purely
    so that permission class's own `view.action` check resolves the same
    way it already does for the real `partial_update` action. Cross-tenant
    upload attempts 404 (`ObjectPermission404Mixin`); same-tenant callers
    without `company.manage` get 403 at the view-permission stage, before
    the object is even fetched.
    """

    permission_classes = [IsAuthenticated, IsPlatformAdminOrCompanyAccess]
    parser_classes = [MultiPartParser, FormParser]
    action = "partial_update"
    permission_code = "company.manage"

    @extend_schema(
        summary="Upload Company Logo",
        description="Upload a JPEG/PNG/WEBP company logo (multipart/form-data, field name `logo`, max 5 MB). Returns an absolute URL usable as Company.logoUrl plus an internal storage key to pass back as logoStorageKey.",
        request={"multipart/form-data": {"type": "object", "properties": {"logo": {"type": "string", "format": "binary"}}}},
        responses={status.HTTP_201_CREATED: CompanyLogoUploadSerializer},
        tags=["Company"],
    )
    def post(self, request: Request, pk: str = None) -> Response:
        company = CompanyService.get_company_by_id(pk)
        self.check_object_permissions(request, company)

        uploaded_file = request.FILES.get("logo")
        result = CompanyService.upload_logo(
            company_id=company.id, uploaded_file=uploaded_file, request=request
        )

        response_data = CompanyLogoUploadSerializer(result).data
        return ApiResponse.created(
            data=response_data, request_id=getattr(request, "request_id", None)
        )
