from django.urls import re_path

from apps.products.views import (
    ProductCategoryViewSet,
    ProductSubcategoryListCreateView,
    ProductSubcategoryViewSet,
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
]
