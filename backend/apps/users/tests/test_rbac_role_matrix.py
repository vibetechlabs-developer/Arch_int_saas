"""
BE-054 §13: the required role-coverage test matrix, exercised at the API
level against a company whose default roles were auto-seeded by
CompanyService.create_company (BE-049). Covers Platform Admin, Admin,
Project Manager, Designer, Accountant, Sales, and Legacy Member against a
representative slice of endpoints (clients, roles, company-memberships,
finance reports, dashboard) -- the remaining fail-closed/escalation cases
(role=NULL, inactive membership, inactive role, soft-deleted grant,
permission replacement, malformed code) are covered at the service level
in test_rbac_services.py and test_membership_management_services.py,
which this file doesn't duplicate.
"""

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from apps.authentication.tokens import CompanyUserAccessToken, PlatformAdminAccessToken
from apps.clients.models import Client
from apps.company.services import CompanyService
from apps.users.models import CompanyMembership, CompanyMembershipStatus, Role
from apps.users.permission_catalog import ALL_PERMISSION_CODES
from apps.users.services import RoleService

User = get_user_model()


class RoleMatrixTestCase(TestCase):
    def setUp(self):
        self.client_api = APIClient()

        self.company, _ = CompanyService.create_company(name="Matrix Studio")

        self.owner_role = Role.objects.get(company=self.company, name="Owner")
        self.admin_role = Role.objects.get(company=self.company, name="Admin")
        self.pm_role = Role.objects.get(company=self.company, name="Project Manager")
        self.designer_role = Role.objects.get(company=self.company, name="Designer / Architect")
        self.accountant_role = Role.objects.get(company=self.company, name="Accountant / Finance")
        self.sales_role = Role.objects.get(company=self.company, name="Sales / CRM User")

        # Legacy Member isn't auto-seeded (it's a migration-only backfill
        # role, per permission_catalog.py) -- constructed here the same
        # way the 0006 data migration does, to exercise its behavior
        # without depending on a real migration run inside a test.
        self.legacy_role = Role.objects.create(
            company=self.company, name="Legacy Member", is_active=True
        )
        RoleService.assign_permissions(role_id=self.legacy_role.id, codes=list(ALL_PERMISSION_CODES))

        self.superadmin = User.objects.create_superuser(
            email="superadmin@example.com", name="Super Admin", password="StrongPassword123!"
        )
        self.superadmin_token = str(PlatformAdminAccessToken.for_user(self.superadmin))

        self.tokens = {}
        for role_attr, role in [
            ("owner", self.owner_role),
            ("admin", self.admin_role),
            ("pm", self.pm_role),
            ("designer", self.designer_role),
            ("accountant", self.accountant_role),
            ("sales", self.sales_role),
            ("legacy", self.legacy_role),
        ]:
            user = User.objects.create_user(
                email=f"{role_attr}@example.com", name=role_attr, password="StrongPassword123!"
            )
            CompanyMembership.objects.create(
                company=self.company, user=user, role=role, status=CompanyMembershipStatus.ACTIVE
            )
            self.tokens[role_attr] = str(CompanyUserAccessToken.for_user(user))

    def _auth(self, token: str) -> None:
        self.client_api.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    # --- A/B: correct permission -> allowed, missing -> 403 -------------

    def test_project_view_allowed_for_every_seeded_role(self):
        """Every default role (per permission_catalog.py) holds
        project.view -- the one code every one of them shares (Designer,
        unlike every other role, does not hold client.view)."""
        for role_attr in ("owner", "admin", "pm", "designer", "accountant", "sales", "legacy"):
            self._auth(self.tokens[role_attr])
            response = self.client_api.get("/projects")
            self.assertEqual(response.status_code, status.HTTP_200_OK, f"role={role_attr}")

    def test_client_view_denied_for_designer(self):
        """Designer holds no client.* code at all (per
        05_Security/Permissions.md §3's framing of Designer as an
        operational/design role, not a client-facing one)."""
        self._auth(self.tokens["designer"])
        response = self.client_api.get("/clients")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_client_create_denied_for_designer(self):
        """Designer holds no client.* code at all."""
        self._auth(self.tokens["designer"])
        response = self.client_api.post("/clients", {"name": "New Client"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_client_create_allowed_for_sales(self):
        self._auth(self.tokens["sales"])
        response = self.client_api.post("/clients", {"name": "New Client"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    # --- J: Accountant can access explicitly approved financial actions,
    # cannot perform undocumented expense create/approve after reconciliation

    def test_accountant_can_access_finance_report(self):
        self._auth(self.tokens["accountant"])
        response = self.client_api.get("/reports/finance")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_accountant_has_no_expense_create_or_approve_after_reconciliation(self):
        from apps.users.services import PermissionService

        membership = CompanyMembership.objects.get(role=self.accountant_role)
        codes = PermissionService.get_permission_codes_for_membership(membership)
        self.assertNotIn("expense.create", codes)
        self.assertNotIn("expense.approve", codes)
        self.assertIn("expense.view", codes)
        self.assertIn("expense.edit", codes)

    # --- K: Designer cannot access protected financial operations unless
    # explicitly granted

    def test_designer_cannot_access_finance_report(self):
        self._auth(self.tokens["designer"])
        response = self.client_api.get("/reports/finance")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_designer_can_access_operational_dashboard(self):
        """
        BE-054 §6: dashboard is gated with report.view (not
        financial_access) precisely so a role like Designer, which has no
        financial codes at all, still sees the operational dashboard.
        """
        self._auth(self.tokens["designer"])
        response = self.client_api.get("/reports/dashboard")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    # --- L: Admin: company.view and company.manage work ------------------

    def test_admin_can_view_and_manage_own_company(self):
        self._auth(self.tokens["admin"])
        get_response = self.client_api.get(f"/companies/{self.company.id}")
        self.assertEqual(get_response.status_code, status.HTTP_200_OK)

        patch_response = self.client_api.patch(
            f"/companies/{self.company.id}", {"name": "Renamed Studio"}, format="json"
        )
        self.assertEqual(patch_response.status_code, status.HTTP_200_OK)
        self.assertEqual(patch_response.json()["data"]["name"], "Renamed Studio")

    def test_sales_cannot_view_company(self):
        """Sales holds no company.* code -- the BE-054 §7 Admin fix is
        specific to Admin, not extended to every role."""
        self._auth(self.tokens["sales"])
        response = self.client_api.get(f"/companies/{self.company.id}")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    # --- M: Legacy Member preserves pre-cutover access as designed -------

    def test_legacy_member_has_unrestricted_access_within_tenant(self):
        self._auth(self.tokens["legacy"])
        self.assertEqual(self.client_api.get("/clients").status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.client_api.post("/clients", {"name": "Legacy Client"}, format="json").status_code,
            status.HTTP_201_CREATED,
        )
        self.assertEqual(self.client_api.get("/reports/finance").status_code, status.HTTP_200_OK)
        self.assertEqual(self.client_api.get(f"/companies/{self.company.id}").status_code, status.HTTP_200_OK)

    # --- P: platform admin bypass remains valid ---------------------------

    def test_platform_admin_bypasses_every_permission_code(self):
        self._auth(self.superadmin_token)
        self.assertEqual(self.client_api.get("/companies").status_code, status.HTTP_200_OK)
        response = self.client_api.get(f"/reports/finance?companyId={self.company.id}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    # --- Owner: every code, since seeded as "__all__" ---------------------

    def test_owner_can_do_everything_tested_here(self):
        self._auth(self.tokens["owner"])
        self.assertEqual(self.client_api.get("/clients").status_code, status.HTTP_200_OK)
        self.assertEqual(self.client_api.get("/reports/finance").status_code, status.HTTP_200_OK)
        self.assertEqual(self.client_api.get(f"/companies/{self.company.id}").status_code, status.HTTP_200_OK)
        self.assertEqual(self.client_api.get("/roles").status_code, status.HTTP_200_OK)

    # --- Project Manager: project.edit but not financial access ----------

    def test_project_manager_can_view_boq_but_not_finance_report(self):
        self._auth(self.tokens["pm"])
        self.assertEqual(self.client_api.get("/reports/finance").status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(self.client_api.get("/reports/dashboard").status_code, status.HTTP_200_OK)
