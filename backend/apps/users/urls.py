from django.urls import re_path

from apps.users.views import CompanyMembershipViewSet, PermissionListView, RoleViewSet

role_list = RoleViewSet.as_view(
    {
        "get": "list",
        "post": "create",
    }
)

role_detail = RoleViewSet.as_view(
    {
        "get": "retrieve",
        "patch": "partial_update",
        "put": "update",
        "delete": "destroy",
    }
)

role_permissions = RoleViewSet.as_view({"get": "retrieve_permissions", "put": "permissions_action"})

membership_list = CompanyMembershipViewSet.as_view(
    {
        "get": "list",
        "post": "create",
    }
)

membership_add_user = CompanyMembershipViewSet.as_view({"post": "add_user"})

membership_detail = CompanyMembershipViewSet.as_view(
    {
        "get": "retrieve",
        "delete": "destroy",
    }
)

membership_assign_role = CompanyMembershipViewSet.as_view({"post": "assign_role"})
membership_suspend = CompanyMembershipViewSet.as_view({"post": "suspend"})
membership_reactivate = CompanyMembershipViewSet.as_view({"post": "reactivate"})

urlpatterns = [
    re_path(r"^roles/?$", role_list, name="role-list"),
    re_path(
        r"^roles/(?P<pk>[0-9a-fA-F-]{36})/?$",
        role_detail,
        name="role-detail",
    ),
    re_path(
        r"^roles/(?P<pk>[0-9a-fA-F-]{36})/permissions/?$",
        role_permissions,
        name="role-permissions",
    ),
    re_path(r"^permissions/?$", PermissionListView.as_view(), name="permission-list"),
    re_path(r"^company-memberships/?$", membership_list, name="company-membership-list"),
    re_path(r"^company-memberships/add-user/?$", membership_add_user, name="company-membership-add-user"),
    re_path(
        r"^company-memberships/(?P<pk>[0-9a-fA-F-]{36})/?$",
        membership_detail,
        name="company-membership-detail",
    ),
    re_path(
        r"^company-memberships/(?P<pk>[0-9a-fA-F-]{36})/assign-role/?$",
        membership_assign_role,
        name="company-membership-assign-role",
    ),
    re_path(
        r"^company-memberships/(?P<pk>[0-9a-fA-F-]{36})/suspend/?$",
        membership_suspend,
        name="company-membership-suspend",
    ),
    re_path(
        r"^company-memberships/(?P<pk>[0-9a-fA-F-]{36})/reactivate/?$",
        membership_reactivate,
        name="company-membership-reactivate",
    ),
]
