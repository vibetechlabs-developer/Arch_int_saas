from django.urls import re_path

from apps.products.views import (
    ProductCategoryViewSet,
    ProductImageUploadView,
    ProductSubcategoryListCreateView,
    ProductSubcategoryViewSet,
    ProductViewSet,
)

category_list = ProductCategoryViewSet.as_view(
    {
        "get": "list",
        "post": "create",
    }
)

category_detail = ProductCategoryViewSet.as_view(
    {
        "get": "retrieve",
        "patch": "partial_update",
        "put": "update",
        "delete": "destroy",
    }
)

subcategory_detail = ProductSubcategoryViewSet.as_view(
    {
        "get": "retrieve",
        "patch": "partial_update",
        "put": "update",
        "delete": "destroy",
    }
)

product_list = ProductViewSet.as_view(
    {
        "get": "list",
        "post": "create",
    }
)

product_detail = ProductViewSet.as_view(
    {
        "get": "retrieve",
        "patch": "partial_update",
        "put": "update",
        "delete": "destroy",
    }
)

urlpatterns = [
    re_path(r"^product-categories/?$", category_list, name="product-category-list"),
    re_path(
        r"^product-categories/(?P<pk>[0-9a-fA-F-]{36})/?$",
        category_detail,
        name="product-category-detail",
    ),
    re_path(
        r"^product-categories/(?P<category_id>[0-9a-fA-F-]{36})/subcategories/?$",
        ProductSubcategoryListCreateView.as_view(),
        name="product-subcategory-list",
    ),
    re_path(
        r"^product-subcategories/(?P<pk>[0-9a-fA-F-]{36})/?$",
        subcategory_detail,
        name="product-subcategory-detail",
    ),
    re_path(r"^products/?$", product_list, name="product-list"),
    re_path(
        r"^products/images/upload/?$",
        ProductImageUploadView.as_view(),
        name="product-image-upload",
    ),
    re_path(
        r"^products/(?P<pk>[0-9a-fA-F-]{36})/?$",
        product_detail,
        name="product-detail",
    ),
]
