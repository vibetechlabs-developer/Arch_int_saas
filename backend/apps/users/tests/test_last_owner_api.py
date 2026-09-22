"""
BE-069: HTTP-level coverage for system role identity + last-owner
protection -- error envelope shape, tenant isolation, and multi-company
isolation of Owner status. Service-level behavior itself is covered by
test_last_owner_protection.py/test_role_system_key.py; this file exercises
the same invariants through the real view/permission/serializer stack.
"""

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from apps.authentication.tokens import CompanyUserAccessToken
from apps.common.test_utils import make_full_access_membership
from apps.company.services import CompanyService
from apps.users.models import CompanyMembership, CompanyMembershipStatus, Role

User = get_user_model()


class LastOwnerApiTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()

        self.company1, _ = CompanyService.create_company(name="API Owner Co 1")
        self.company2, _ = CompanyService.create_company(name="API Owner Co 2")
        self.owner_role_1 = Role.objects.get(company=self.company1, system_key="owner")
        self.admin_role_1 = Role.objects.get(company=self.company1, system_key="admin")
        self.owner_role_2 = Role.objects.get(company=self.company2, system_key="owner")

        self.owner_user = User.objects.create_user(
            email="owner@company1.com", name="Sole Owner", password="StrongPassword123!"
        )
        self.owner_membership = CompanyMembership.objects.create(
            company=self.company1, user=self.owner_user, role=self.owner_role_1, status=CompanyMembershipStatus.ACTIVE
        )
        self.owner_token = str(CompanyUserAccessToken.for_user(self.owner_user))

        self.other_actor_user = User.objects.create_user(
            email="actor@company1.com", name="Second Actor", password="StrongPassword123!"
        )
        make_full_access_membership(self.company1, self.other_actor_user)
        self.other_actor_token = str(CompanyUserAccessToken.for_user(self.other_actor_user))

        self.other_company_user = User.objects.create_user(
            email="owner2@company2.com", name="Company 2 Owner", password="StrongPassword123!"
        )
        make_full_access_membership(self.company2, self.other_company_user)
        self.other_company_token = str(CompanyUserAccessToken.for_user(self.other_company_user))

    # --- Error envelope shape -----------------------------------------------

    def test_last_owner_rejection_uses_standard_409_envelope(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.other_actor_token}")
        response = self.client.post(
            f"/company-memberships/{self.owner_membership.id}/assign-role",
            {"roleId": str(self.admin_role_1.id)},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        body = response.json()
        self.assertFalse(body["success"])
        self.assertEqual(body["error"]["code"], "LAST_OWNER_REQUIRED")
        self.assertIn("Owner", body["error"]["message"])

    def test_owner_role_delete_rejection_uses_standard_409_envelope(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.other_actor_token}")
        response = self.client.delete(f"/roles/{self.owner_role_1.id}")
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        body = response.json()
        self.assertEqual(body["error"]["code"], "SYSTEM_ROLE_PROTECTED")

    # --- Cross-tenant / same-tenant authorization unaffected ----------------

    def test_cross_tenant_owner_role_delete_returns_404_not_409(self):
        """
        A caller in Company 2 targeting Company 1's Owner role by id must
        get the standard cross-tenant 404 -- the new SYSTEM_ROLE_PROTECTED
        conflict must never leak that a role with this id exists at all
        in another tenant.
        """
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.other_company_token}")
        response = self.client.delete(f"/roles/{self.owner_role_1.id}")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_cross_tenant_assign_role_returns_404(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.other_company_token}")
        response = self.client.post(
            f"/company-memberships/{self.owner_membership.id}/assign-role",
            {"roleId": str(self.admin_role_1.id)},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_same_tenant_unauthorized_actor_still_gets_403_not_409(self):
        """A caller with no role.manage/user.manage at all should be blocked at the permission layer (403) before ever reaching the last-owner check."""
        no_permission_user = User.objects.create_user(
            email="noperm@company1.com", name="No Perm", password="StrongPassword123!"
        )
        CompanyMembership.objects.create(
            company=self.company1, user=no_permission_user, status=CompanyMembershipStatus.ACTIVE
        )
        token = str(CompanyUserAccessToken.for_user(no_permission_user))
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

        response = self.client.post(
            f"/company-memberships/{self.owner_membership.id}/assign-role",
            {"roleId": str(self.admin_role_1.id)},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    # --- Privilege escalation regression, combined with new logic ----------

    def test_privilege_escalation_guard_still_blocks_assigning_owner_role(self):
        """
        A non-owner actor without every catalog permission code still
        cannot assign the Owner role to anyone (BE-054's escalation
        guard) -- confirms the new last-owner check doesn't accidentally
        bypass or short-circuit the pre-existing escalation check.
        """
        limited_role = Role.objects.create(
            company=self.company1, name="Limited Manager", is_active=True
        )
        from apps.users.models import Permission, RolePermission

        RolePermission.objects.create(
            role=limited_role, permission=Permission.objects.get(code="user.manage")
        )
        limited_user = User.objects.create_user(
            email="limited@company1.com", name="Limited Manager", password="StrongPassword123!"
        )
        CompanyMembership.objects.create(
            company=self.company1, user=limited_user, role=limited_role, status=CompanyMembershipStatus.ACTIVE
        )
        token = str(CompanyUserAccessToken.for_user(limited_user))
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

        other_member = User.objects.create_user(
            email="other-member@company1.com", name="Other Member", password="StrongPassword123!"
        )
        other_membership = CompanyMembership.objects.create(
            company=self.company1, user=other_member, status=CompanyMembershipStatus.ACTIVE
        )

        response = self.client.post(
            f"/company-memberships/{other_membership.id}/assign-role",
            {"roleId": str(self.owner_role_1.id)},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    # --- Add User regression -------------------------------------------------

    def test_add_user_into_owner_role_still_works(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.other_actor_token}")
        response = self.client.post(
            "/company-memberships/add-user",
            {"email": "new-owner@company1.com", "name": "New Owner", "roleId": str(self.owner_role_1.id)},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        data = response.json()["data"]
        self.assertEqual(data["membership"]["roleSystemKey"], "owner")

        # Now two active owners -- the original sole owner can be safely demoted.
        response2 = self.client.post(
            f"/company-memberships/{self.owner_membership.id}/assign-role",
            {"roleId": str(self.admin_role_1.id)},
            format="json",
        )
        self.assertEqual(response2.status_code, status.HTTP_200_OK)

    # --- Multi-company isolation ---------------------------------------------

    def test_owner_status_is_isolated_per_company(self):
        """
        A user who is the sole Owner of Company 1 and merely an Admin
        member of Company 2 must be protected in Company 1 but freely
        removable in Company 2 -- system_key/last-owner status never
        leaks across tenants.
        """
        admin_role_2 = Role.objects.get(company=self.company2, system_key="admin")
        multi_membership = CompanyMembership.objects.create(
            company=self.company2,
            user=self.owner_user,
            role=admin_role_2,
            status=CompanyMembershipStatus.ACTIVE,
        )

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.other_company_token}")
        response = self.client.delete(f"/company-memberships/{multi_membership.id}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Still fully protected as Owner in Company 1.
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.other_actor_token}")
        response2 = self.client.delete(f"/company-memberships/{self.owner_membership.id}")
        self.assertEqual(response2.status_code, status.HTTP_409_CONFLICT)

    def test_role_permission_readback_unaffected_by_system_key(self):
        """22. Role permission read-back still works, now also exposing systemKey/isSystem on the role list without disturbing the existing permission read-back contract."""
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.other_actor_token}")
        response = self.client.get(f"/roles/{self.owner_role_1.id}/permissions")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        codes = response.json()["data"]["permissionCodes"]
        self.assertIn("company.manage", codes)
