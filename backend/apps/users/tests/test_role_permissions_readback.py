from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from apps.audit.models import AuditLog
from apps.authentication.tokens import CompanyUserAccessToken, PlatformAdminAccessToken
from apps.common.test_utils import make_full_access_membership
from apps.company.models import Company, CompanyStatus
from apps.users.models import CompanyMembership, CompanyMembershipStatus, Permission, Role, RolePermission
from apps.users.repositories import PermissionRepository

User = get_user_model()


class RolePermissionsReadBackTestCase(TestCase):
    """
    Integration tests for GET /roles/{id}/permissions (BE-072) — the
    read-back companion to the existing PUT on the same URL. Every
    assertion here checks persisted RolePermission rows, never
    DEFAULT_ROLE_PERMISSIONS or any other seed/default data.
    """

    def setUp(self):
        self.client = APIClient()
        self.company1 = Company.objects.create(name="Studio One", status=CompanyStatus.ACTIVE)
        self.company2 = Company.objects.create(name="Studio Two", status=CompanyStatus.ACTIVE)

        self.admin_user = User.objects.create_user(
            email="admin@company1.com", name="Admin User", password="StrongPassword123!"
        )
        make_full_access_membership(self.company1, self.admin_user)
        self.admin_token = str(CompanyUserAccessToken.for_user(self.admin_user))

        self.role1 = Role.objects.create(company=self.company1, name="Custom", is_active=True)
        self.role_c2 = Role.objects.create(company=self.company2, name="OtherCo Role", is_active=True)

        self.view_permission = Permission.objects.get(code="project.view")
        self.edit_permission = Permission.objects.get(code="project.edit")
        self.invoice_permission = Permission.objects.get(code="invoice.view")

    def _grant(self, role, *permissions):
        for permission in permissions:
            RolePermission.objects.create(role=role, permission=permission)

    # -- basic read-back -----------------------------------------------

    def test_returns_persisted_grants_not_defaults(self):
        self._grant(self.role1, self.view_permission, self.edit_permission)

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.admin_token}")
        response = self.client.get(f"/roles/{self.role1.id}/permissions")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()["data"]
        self.assertEqual(data["roleId"], str(self.role1.id))
        self.assertEqual(set(data["permissionCodes"]), {"project.view", "project.edit"})

    def test_empty_permission_set(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.admin_token}")
        response = self.client.get(f"/roles/{self.role1.id}/permissions")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["data"]["permissionCodes"], [])

    def test_only_this_roles_grants_are_returned(self):
        other_role = Role.objects.create(company=self.company1, name="Other Role", is_active=True)
        self._grant(self.role1, self.view_permission)
        self._grant(other_role, self.invoice_permission)

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.admin_token}")
        response = self.client.get(f"/roles/{self.role1.id}/permissions")

        codes = response.json()["data"]["permissionCodes"]
        self.assertEqual(codes, ["project.view"])
        self.assertNotIn("invoice.view", codes)

    def test_soft_deleted_grant_is_not_returned(self):
        grant = RolePermission.objects.create(role=self.role1, permission=self.view_permission)
        RolePermission.objects.create(role=self.role1, permission=self.edit_permission)
        grant.delete()  # soft-delete

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.admin_token}")
        response = self.client.get(f"/roles/{self.role1.id}/permissions")

        self.assertEqual(response.json()["data"]["permissionCodes"], ["project.edit"])

    # -- tenant isolation / not found ------------------------------------

    def test_cross_tenant_role_returns_404(self):
        self._grant(self.role_c2, self.view_permission)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.admin_token}")
        response = self.client.get(f"/roles/{self.role_c2.id}/permissions")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_nonexistent_role_returns_404(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.admin_token}")
        response = self.client.get("/roles/00000000-0000-0000-0000-000000000000/permissions")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_unauthenticated_returns_401(self):
        response = self.client.get(f"/roles/{self.role1.id}/permissions")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_missing_role_view_permission_returns_403(self):
        limited_role = Role.objects.create(company=self.company1, name="Limited", is_active=True)
        limited_user = User.objects.create_user(
            email="limited@company1.com", name="Limited User", password="StrongPassword123!"
        )
        CompanyMembership.objects.create(
            company=self.company1, user=limited_user, role=limited_role, status=CompanyMembershipStatus.ACTIVE
        )
        limited_token = str(CompanyUserAccessToken.for_user(limited_user))

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {limited_token}")
        response = self.client.get(f"/roles/{self.role1.id}/permissions")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_inactive_role_grants_still_readable(self):
        """
        An inactive role can't be newly *assigned* to a member (validated
        elsewhere), but its own existing grants must still be readable —
        an admin re-activating a role needs to see what it already holds.
        """
        self.role1.is_active = False
        self.role1.save()
        self._grant(self.role1, self.view_permission)

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.admin_token}")
        response = self.client.get(f"/roles/{self.role1.id}/permissions")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["data"]["permissionCodes"], ["project.view"])

    def test_platform_admin_can_read_any_companys_role_permissions(self):
        self._grant(self.role_c2, self.invoice_permission)
        superadmin = User.objects.create_superuser(
            email="super@example.com", name="Super Admin", password="StrongPassword123!"
        )
        token = str(PlatformAdminAccessToken.for_user(superadmin))

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        response = self.client.get(f"/roles/{self.role_c2.id}/permissions")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["data"]["permissionCodes"], ["invoice.view"])

    # -- write-then-read lifecycle ----------------------------------------

    def test_assignment_persists_and_is_reflected_on_subsequent_get(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.admin_token}")

        put_response = self.client.put(
            f"/roles/{self.role1.id}/permissions",
            {"permissionCodes": ["project.view", "invoice.view"]},
            format="json",
        )
        self.assertEqual(put_response.status_code, status.HTTP_200_OK)

        get_response = self.client.get(f"/roles/{self.role1.id}/permissions")
        self.assertEqual(set(get_response.json()["data"]["permissionCodes"]), {"project.view", "invoice.view"})

    def test_removing_a_grant_is_reflected_on_subsequent_get(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.admin_token}")
        self.client.put(
            f"/roles/{self.role1.id}/permissions",
            {"permissionCodes": ["project.view", "invoice.view"]},
            format="json",
        )

        self.client.put(
            f"/roles/{self.role1.id}/permissions",
            {"permissionCodes": ["project.view"]},
            format="json",
        )

        response = self.client.get(f"/roles/{self.role1.id}/permissions")
        self.assertEqual(response.json()["data"]["permissionCodes"], ["project.view"])

    def test_put_replaces_the_entire_set_not_a_delta(self):
        """
        Confirms replace-all semantics directly through the persisted
        read-back: granting ["invoice.view"] after ["project.view",
        "project.edit"] already existed must leave ONLY invoice.view,
        never project.view/project.edit still present.
        """
        self._grant(self.role1, self.view_permission, self.edit_permission)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.admin_token}")

        self.client.put(
            f"/roles/{self.role1.id}/permissions",
            {"permissionCodes": ["invoice.view"]},
            format="json",
        )

        response = self.client.get(f"/roles/{self.role1.id}/permissions")
        self.assertEqual(response.json()["data"]["permissionCodes"], ["invoice.view"])
        self.assertEqual(PermissionRepository.codes_for_role(self.role1.id), {"invoice.view"})

    # -- privilege escalation (regression, not new behavior) --------------

    def test_privilege_escalation_still_blocked_on_assignment(self):
        limited_role = Role.objects.create(company=self.company1, name="Limited", is_active=True)
        RolePermission.objects.create(role=limited_role, permission=self.view_permission)
        limited_user = User.objects.create_user(
            email="limited2@company1.com", name="Limited User", password="StrongPassword123!"
        )
        CompanyMembership.objects.create(
            company=self.company1, user=limited_user, role=limited_role, status=CompanyMembershipStatus.ACTIVE
        )
        limited_token = str(CompanyUserAccessToken.for_user(limited_user))

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {limited_token}")
        response = self.client.put(
            f"/roles/{limited_role.id}/permissions",
            {"permissionCodes": ["project.view", "invoice.view", "role.manage"]},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        # Confirm nothing was actually granted despite the rejected request.
        self.assertEqual(PermissionRepository.codes_for_role(limited_role.id), {"project.view"})

    # -- audit noise --------------------------------------------------------

    def test_read_does_not_write_an_audit_entry(self):
        before_count = AuditLog.objects.filter(entity_type="role_permission", entity_id=self.role1.id).count()

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.admin_token}")
        self.client.get(f"/roles/{self.role1.id}/permissions")

        after_count = AuditLog.objects.filter(entity_type="role_permission", entity_id=self.role1.id).count()
        self.assertEqual(before_count, after_count)

    def test_mutation_still_writes_an_audit_entry(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.admin_token}")
        self.client.put(
            f"/roles/{self.role1.id}/permissions",
            {"permissionCodes": ["project.view"]},
            format="json",
        )
        self.assertTrue(
            AuditLog.objects.filter(entity_type="role_permission", entity_id=self.role1.id).exists()
        )

    def test_response_contains_no_unrelated_tenant_grants(self):
        self._grant(self.role1, self.view_permission)
        self._grant(self.role_c2, self.invoice_permission, self.edit_permission)

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.admin_token}")
        response = self.client.get(f"/roles/{self.role1.id}/permissions")

        codes = response.json()["data"]["permissionCodes"]
        self.assertEqual(codes, ["project.view"])
        self.assertNotIn("invoice.view", codes)
