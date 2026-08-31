from django.urls import re_path

from apps.products.views import ProductCategoryViewSet

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

urlpatterns = [
    re_path(r"^product-categories/?$", category_list, name="product-category-list"),
    re_path(
        r"^product-categories/(?P<pk>[0-9a-fA-F-]{36})/?$",
        category_detail,
        name="product-category-detail",
    ),
]
