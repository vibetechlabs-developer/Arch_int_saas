from drf_spectacular.utils import OpenApiParameter, extend_schema, extend_schema_view
from rest_framework import status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

from apps.common.pagination import StandardPagination
from apps.common.responses import ApiResponse
from apps.common.views import ObjectPermission404Mixin
from apps.products.models import ProductCategory
from apps.products.permissions import ProductCategoryPermission
from apps.products.serializers import (
    ProductCategoryCreateSerializer,
    ProductCategoryListQuerySerializer,
    ProductCategorySerializer,
    ProductCategoryUpdateSerializer,
)
from apps.products.services import ProductCategoryService
from apps.users.permissions import is_platform_admin


@extend_schema_view(
    list=extend_schema(
        summary="List Product Categories",
        description="List tenant product categories with ordering.",
        parameters=[
            OpenApiParameter(
                name="ordering",
                description="Ordering field (e.g. name, -name, created_at, -created_at).",
                required=False,
                type=str,
            ),
        ],
        responses={status.HTTP_200_OK: ProductCategorySerializer(many=True)},
        tags=["Product Catalog"],
    ),
    create=extend_schema(
        summary="Create Product Category",
        description="Create a new product category for a company tenant.",
        request=ProductCategoryCreateSerializer,
        responses={status.HTTP_201_CREATED: ProductCategorySerializer},
        tags=["Product Catalog"],
    ),
    retrieve=extend_schema(
        summary="Retrieve Product Category",
        description="Retrieve product category details by UUID.",
        responses={status.HTTP_200_OK: ProductCategorySerializer},
        tags=["Product Catalog"],
    ),
    partial_update=extend_schema(
        summary="Update Product Category",
        description="Partially update product category details by UUID.",
        request=ProductCategoryUpdateSerializer,
        responses={status.HTTP_200_OK: ProductCategorySerializer},
        tags=["Product Catalog"],
    ),
    update=extend_schema(
        summary="Full Update Product Category",
        description="Update forwards to partial_update logic.",
        request=ProductCategoryUpdateSerializer,
        responses={status.HTTP_200_OK: ProductCategorySerializer},
        tags=["Product Catalog"],
    ),
    destroy=extend_schema(
        summary="Delete Product Category",
        description="Soft-delete a product category by UUID.",
        responses={status.HTTP_200_OK: ProductCategorySerializer},
        tags=["Product Catalog"],
    ),
)
class ProductCategoryViewSet(ObjectPermission404Mixin, viewsets.GenericViewSet):
    """
    ViewSet for ProductCategory CRUD operations (BE-031). Mirrors
    apps.clients.views.ClientViewSet exactly — orchestration only, all
    business logic lives in ProductCategoryService.
    """

    permission_classes = [IsAuthenticated, ProductCategoryPermission]
    pagination_class = StandardPagination
    serializer_class = ProductCategorySerializer
    queryset = ProductCategory.objects.none()

    def list(self, request: Request) -> Response:
        query = ProductCategoryListQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        validated = query.validated_data

        queryset = ProductCategoryService.list_categories_for_viewer(
            is_platform_admin=is_platform_admin(request),
            resolved_company_id=request.company_id,
            admin_company_id_param=None,
            ordering=validated["ordering"],
        )

        page = self.paginate_queryset(queryset)
        request_id = getattr(request, "request_id", None)

        if page is not None:
            serializer = ProductCategorySerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = ProductCategorySerializer(queryset, many=True)
        return ApiResponse.success(data=serializer.data, request_id=request_id)

    def create(self, request: Request) -> Response:
        serializer = ProductCategoryCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated = serializer.validated_data

        target_company_id = ProductCategoryService.resolve_create_target_company_id(
            is_platform_admin=is_platform_admin(request),
            resolved_company_id=request.company_id,
            supplied_company_id=validated.get("company_id"),
        )

        category = ProductCategoryService.create_category(
            company_id=target_company_id,
            name=validated["name"],
            actor_user=request.user,
            request=request,
        )

        response_data = ProductCategorySerializer(category).data
        request_id = getattr(request, "request_id", None)

        return ApiResponse.created(data=response_data, request_id=request_id)

    def retrieve(self, request: Request, pk: str = None) -> Response:
        category = ProductCategoryService.get_category_by_id(pk)
        self.check_object_permissions(request, category)

        response_data = ProductCategorySerializer(category).data
        request_id = getattr(request, "request_id", None)

        return ApiResponse.success(data=response_data, request_id=request_id)

    def partial_update(self, request: Request, pk: str = None) -> Response:
        category = ProductCategoryService.get_category_by_id(pk)
        self.check_object_permissions(request, category)

        serializer = ProductCategoryUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        updated_category = ProductCategoryService.update_category(
            category_id=pk,
            validated_data=serializer.validated_data,
            actor_user=request.user,
            request=request,
        )
        response_data = ProductCategorySerializer(updated_category).data
        request_id = getattr(request, "request_id", None)

        return ApiResponse.success(data=response_data, request_id=request_id)

    def update(self, request: Request, pk: str = None) -> Response:
        """
        Full update forwards to partial_update logic — matching the
        existing convention (RoleViewSet/ClientViewSet/ProjectViewSet).
        """
        return self.partial_update(request, pk=pk)

    def destroy(self, request: Request, pk: str = None) -> Response:
        category = ProductCategoryService.get_category_by_id(pk)
        self.check_object_permissions(request, category)

        ProductCategoryService.soft_delete_category(pk, actor_user=request.user, request=request)
        request_id = getattr(request, "request_id", None)

        return ApiResponse.success(
            data={"message": "Product category deleted successfully."},
            request_id=request_id,
        )
