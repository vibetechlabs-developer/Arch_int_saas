from drf_spectacular.utils import OpenApiParameter, extend_schema, extend_schema_view
from rest_framework import exceptions as drf_exceptions
from rest_framework import status, viewsets
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.pagination import StandardPagination
from apps.common.responses import ApiResponse
from apps.common.views import ObjectPermission404Mixin
from apps.products.models import Product, ProductCategory, ProductSubcategory
from apps.products.permissions import ProductCategoryPermission
from apps.products.serializers import (
    ProductCategoryCreateSerializer,
    ProductCategoryListQuerySerializer,
    ProductCategorySerializer,
    ProductCategoryUpdateSerializer,
    ProductCreateSerializer,
    ProductImageUploadSerializer,
    ProductListQuerySerializer,
    ProductSerializer,
    ProductSubcategoryCreateSerializer,
    ProductSubcategoryListQuerySerializer,
    ProductSubcategorySerializer,
    ProductSubcategoryUpdateSerializer,
    ProductUpdateSerializer,
)
from apps.products.services import (
    ProductCategoryService,
    ProductImageService,
    ProductService,
    ProductSubcategoryService,
)
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
    permission_code_map = {
        "list": "product.view",
        "create": "product.manage",
        "retrieve": "product.view",
        "partial_update": "product.manage",
        "update": "product.manage",
        "destroy": "product.manage",
    }

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


class ProductSubcategoryListCreateView(ObjectPermission404Mixin, APIView):
    """
    `GET`/`POST /product-categories/{categoryId}/subcategories` (BE-032),
    matching BOQ_API.md's nested endpoint shape exactly. Reuses
    ProductCategoryPermission directly (its object-level check only
    inspects `obj.company_id`, so it works unchanged against the parent
    Category here) — mirrors ProjectTeamView's reasoning for not building
    a separate permission class for a check that's identical either way.
    """

    permission_classes = [IsAuthenticated, ProductCategoryPermission]
    permission_code_map = {"get": "product.view", "post": "product.manage"}

    @extend_schema(
        summary="List Product Subcategories",
        description="List the subcategories under one product category.",
        parameters=[
            OpenApiParameter(
                name="ordering",
                description="Ordering field (e.g. name, -name, created_at, -created_at).",
                required=False,
                type=str,
            ),
        ],
        responses={status.HTTP_200_OK: ProductSubcategorySerializer(many=True)},
        tags=["Product Catalog"],
    )
    def get(self, request: Request, category_id: str = None) -> Response:
        category = ProductCategoryService.get_category_by_id(category_id)
        self.check_object_permissions(request, category)

        query = ProductSubcategoryListQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)

        subcategories = ProductSubcategoryService.list_subcategories_for_category(
            category, ordering=query.validated_data["ordering"]
        )
        serializer = ProductSubcategorySerializer(subcategories, many=True)
        return ApiResponse.success(
            data=serializer.data, request_id=getattr(request, "request_id", None)
        )

    @extend_schema(
        summary="Create Product Subcategory",
        description="Create a new subcategory under one product category.",
        request=ProductSubcategoryCreateSerializer,
        responses={status.HTTP_201_CREATED: ProductSubcategorySerializer},
        tags=["Product Catalog"],
    )
    def post(self, request: Request, category_id: str = None) -> Response:
        category = ProductCategoryService.get_category_by_id(category_id)
        self.check_object_permissions(request, category)

        serializer = ProductSubcategoryCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        subcategory = ProductSubcategoryService.create_subcategory(
            category=category,
            name=serializer.validated_data["name"],
            actor_user=request.user,
            request=request,
        )

        response_data = ProductSubcategorySerializer(subcategory).data
        return ApiResponse.created(
            data=response_data, request_id=getattr(request, "request_id", None)
        )


@extend_schema_view(
    retrieve=extend_schema(
        summary="Retrieve Product Subcategory",
        description="Retrieve product subcategory details by UUID.",
        responses={status.HTTP_200_OK: ProductSubcategorySerializer},
        tags=["Product Catalog"],
    ),
    partial_update=extend_schema(
        summary="Update Product Subcategory",
        description="Partially update product subcategory details by UUID.",
        request=ProductSubcategoryUpdateSerializer,
        responses={status.HTTP_200_OK: ProductSubcategorySerializer},
        tags=["Product Catalog"],
    ),
    update=extend_schema(
        summary="Full Update Product Subcategory",
        description="Update forwards to partial_update logic.",
        request=ProductSubcategoryUpdateSerializer,
        responses={status.HTTP_200_OK: ProductSubcategorySerializer},
        tags=["Product Catalog"],
    ),
    destroy=extend_schema(
        summary="Delete Product Subcategory",
        description="Soft-delete a product subcategory by UUID.",
        responses={status.HTTP_200_OK: ProductSubcategorySerializer},
        tags=["Product Catalog"],
    ),
)
class ProductSubcategoryViewSet(ObjectPermission404Mixin, viewsets.GenericViewSet):
    """
    Flat detail-only actions for ProductSubcategory
    (`/product-subcategories/{id}`, BE-032) — list/create are nested under
    Category (ProductSubcategoryListCreateView above), matching
    BOQ_API.md's documented shape; only retrieve/update/delete use the
    subcategory's own id directly, the same split ProjectTeamView/
    ProjectViewSet use for Project Members.
    """

    permission_classes = [IsAuthenticated, ProductCategoryPermission]
    serializer_class = ProductSubcategorySerializer
    queryset = ProductSubcategory.objects.none()
    permission_code_map = {
        "retrieve": "product.view",
        "partial_update": "product.manage",
        "update": "product.manage",
        "destroy": "product.manage",
    }

    def retrieve(self, request: Request, pk: str = None) -> Response:
        subcategory = ProductSubcategoryService.get_subcategory_by_id(pk)
        self.check_object_permissions(request, subcategory)

        response_data = ProductSubcategorySerializer(subcategory).data
        return ApiResponse.success(
            data=response_data, request_id=getattr(request, "request_id", None)
        )

    def partial_update(self, request: Request, pk: str = None) -> Response:
        subcategory = ProductSubcategoryService.get_subcategory_by_id(pk)
        self.check_object_permissions(request, subcategory)

        serializer = ProductSubcategoryUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        updated_subcategory = ProductSubcategoryService.update_subcategory(
            subcategory_id=pk,
            validated_data=serializer.validated_data,
            actor_user=request.user,
            request=request,
        )
        response_data = ProductSubcategorySerializer(updated_subcategory).data
        return ApiResponse.success(
            data=response_data, request_id=getattr(request, "request_id", None)
        )

    def update(self, request: Request, pk: str = None) -> Response:
        """
        Full update forwards to partial_update logic — matching the
        existing convention.
        """
        return self.partial_update(request, pk=pk)

    def destroy(self, request: Request, pk: str = None) -> Response:
        subcategory = ProductSubcategoryService.get_subcategory_by_id(pk)
        self.check_object_permissions(request, subcategory)

        ProductSubcategoryService.soft_delete_subcategory(
            pk, actor_user=request.user, request=request
        )
        return ApiResponse.success(
            data={"message": "Product subcategory deleted successfully."},
            request_id=getattr(request, "request_id", None),
        )


@extend_schema_view(
    list=extend_schema(
        summary="List Products",
        description="List tenant products. Filterable by category/subcategory/status, orderable via ?ordering=.",
        parameters=[
            OpenApiParameter(
                name="category",
                description="Filter by ProductCategory UUID (matches via the product's subcategory).",
                required=False,
                type=str,
            ),
            OpenApiParameter(
                name="subcategory",
                description="Filter by ProductSubcategory UUID.",
                required=False,
                type=str,
            ),
            OpenApiParameter(
                name="status",
                description="Filter by status (active, inactive).",
                required=False,
                type=str,
            ),
            OpenApiParameter(
                name="ordering",
                description="Ordering field (e.g. name, -name, created_at, -created_at).",
                required=False,
                type=str,
            ),
        ],
        responses={status.HTTP_200_OK: ProductSerializer(many=True)},
        tags=["Product Catalog"],
    ),
    create=extend_schema(
        summary="Create Product",
        description="Create a new product/work item for a company tenant.",
        request=ProductCreateSerializer,
        responses={status.HTTP_201_CREATED: ProductSerializer},
        tags=["Product Catalog"],
    ),
    retrieve=extend_schema(
        summary="Retrieve Product",
        description="Retrieve product details by UUID.",
        responses={status.HTTP_200_OK: ProductSerializer},
        tags=["Product Catalog"],
    ),
    partial_update=extend_schema(
        summary="Update Product",
        description="Partially update product details by UUID.",
        request=ProductUpdateSerializer,
        responses={status.HTTP_200_OK: ProductSerializer},
        tags=["Product Catalog"],
    ),
    update=extend_schema(
        summary="Full Update Product",
        description="Update forwards to partial_update logic.",
        request=ProductUpdateSerializer,
        responses={status.HTTP_200_OK: ProductSerializer},
        tags=["Product Catalog"],
    ),
    destroy=extend_schema(
        summary="Delete Product",
        description="Soft-delete a product by UUID.",
        responses={status.HTTP_200_OK: ProductSerializer},
        tags=["Product Catalog"],
    ),
)
class ProductViewSet(ObjectPermission404Mixin, viewsets.GenericViewSet):
    """
    ViewSet for Product CRUD operations (BE-033) plus list filtering
    (BE-034). Mirrors ProductCategoryViewSet/ProjectViewSet exactly —
    orchestration only, all business logic lives in ProductService. No
    audit calls here (wired inline in ProductService, not deferred — see
    class docstring there).
    """

    permission_classes = [IsAuthenticated, ProductCategoryPermission]
    pagination_class = StandardPagination
    serializer_class = ProductSerializer
    queryset = Product.objects.none()
    permission_code_map = {
        "list": "product.view",
        "create": "product.manage",
        "retrieve": "product.view",
        "partial_update": "product.manage",
        "update": "product.manage",
        "destroy": "product.manage",
    }

    def list(self, request: Request) -> Response:
        query = ProductListQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        validated = query.validated_data

        queryset = ProductService.list_products_for_viewer(
            is_platform_admin=is_platform_admin(request),
            resolved_company_id=request.company_id,
            admin_company_id_param=None,
            category_id=validated["category_id"],
            subcategory_id=validated["subcategory_id"],
            status=validated["status"],
            ordering=validated["ordering"],
        )

        page = self.paginate_queryset(queryset)
        request_id = getattr(request, "request_id", None)

        if page is not None:
            serializer = ProductSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = ProductSerializer(queryset, many=True)
        return ApiResponse.success(data=serializer.data, request_id=request_id)

    def create(self, request: Request) -> Response:
        serializer = ProductCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated = serializer.validated_data

        target_company_id = ProductService.resolve_create_target_company_id(
            is_platform_admin=is_platform_admin(request),
            resolved_company_id=request.company_id,
            supplied_company_id=validated.get("company_id"),
        )

        product = ProductService.create_product(
            company_id=target_company_id,
            subcategory_id=validated["subcategory_id"],
            name=validated["name"],
            image_url=validated.get("image_url", ""),
            image_storage_key=validated.get("image_storage_key", ""),
            unit=validated.get("unit", ""),
            default_cost=validated.get("default_cost"),
            default_selling_rate=validated.get("default_selling_rate"),
            tax_rate=validated.get("tax_rate"),
            status=validated.get("status"),
            actor_user=request.user,
            request=request,
        )

        response_data = ProductSerializer(product).data
        request_id = getattr(request, "request_id", None)

        return ApiResponse.created(data=response_data, request_id=request_id)

    def retrieve(self, request: Request, pk: str = None) -> Response:
        product = ProductService.get_product_by_id(pk)
        self.check_object_permissions(request, product)

        response_data = ProductSerializer(product).data
        request_id = getattr(request, "request_id", None)

        return ApiResponse.success(data=response_data, request_id=request_id)

    def partial_update(self, request: Request, pk: str = None) -> Response:
        product = ProductService.get_product_by_id(pk)
        self.check_object_permissions(request, product)

        serializer = ProductUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        updated_product = ProductService.update_product(
            product_id=pk,
            validated_data=serializer.validated_data,
            actor_user=request.user,
            request=request,
        )
        response_data = ProductSerializer(updated_product).data
        request_id = getattr(request, "request_id", None)

        return ApiResponse.success(data=response_data, request_id=request_id)

    def update(self, request: Request, pk: str = None) -> Response:
        """
        Full update forwards to partial_update logic — matching the
        existing convention.
        """
        return self.partial_update(request, pk=pk)

    def destroy(self, request: Request, pk: str = None) -> Response:
        product = ProductService.get_product_by_id(pk)
        self.check_object_permissions(request, product)

        ProductService.soft_delete_product(pk, actor_user=request.user, request=request)
        request_id = getattr(request, "request_id", None)

        return ApiResponse.success(
            data={"message": "Product deleted successfully."},
            request_id=request_id,
        )


class ProductImageUploadView(APIView):
    """
    `POST /products/images/upload`. Deliberately its own top-level route
    (not nested under `ProductViewSet`) — an uploaded image is not yet
    attached to any particular Product (it may back a Create Product form
    before that Product exists at all), so there is no `{id}` to nest
    under. Gated by `product.manage` — the same code Product create/update
    already require — since selecting a catalog image is part of managing
    the catalog, not merely viewing it.
    """

    permission_classes = [IsAuthenticated, ProductCategoryPermission]
    parser_classes = [MultiPartParser, FormParser]
    permission_code = "product.manage"

    @extend_schema(
        summary="Upload Product Image",
        description="Upload a JPEG/PNG/WEBP product image (multipart/form-data, field name `image`, max 5 MB). Returns an absolute URL usable as Product.imageUrl.",
        request={"multipart/form-data": {"type": "object", "properties": {"image": {"type": "string", "format": "binary"}}}},
        responses={status.HTTP_201_CREATED: ProductImageUploadSerializer},
        tags=["Product Catalog"],
    )
    def post(self, request: Request) -> Response:
        if is_platform_admin(request):
            company_id = request.query_params.get("companyId")
            if not company_id:
                raise drf_exceptions.ValidationError(
                    {"companyId": ["companyId is required for platform admin image upload."]}
                )
        else:
            company_id = request.company_id

        uploaded_file = request.FILES.get("image")
        result = ProductImageService.upload_image(
            company_id=company_id, uploaded_file=uploaded_file, request=request
        )

        response_data = ProductImageUploadSerializer(result).data
        return ApiResponse.created(
            data=response_data, request_id=getattr(request, "request_id", None)
        )
