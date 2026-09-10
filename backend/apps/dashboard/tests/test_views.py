from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from apps.authentication.tokens import CompanyUserAccessToken, PlatformAdminAccessToken
from apps.clients.models import Client
from apps.common.test_utils import make_full_access_membership
from apps.company.models import Company, CompanyStatus
from apps.invoices.services import InvoiceService
from apps.payments.services import PaymentService
from apps.projects.models import Project
from apps.users.models import CompanyMembership, CompanyMembershipStatus, Permission, Role, RolePermission

User = get_user_model()


def make_report_view_only_membership(company, user):
    """
    A membership whose role holds `report.view` but deliberately NOT
    `report.financial_access` -- the exact "operational-only" caller
    BE-068 is about. No role-name/display matching anywhere: the role is
    literally named something unrelated ("Ops Viewer") to prove the
    restriction comes from the permission code, not the name.
    """
    role = Role.objects.create(company=company, name="Ops Viewer", is_active=True)
    RolePermission.objects.create(role=role, permission=Permission.objects.get(code="report.view"))
    return CompanyMembership.objects.create(
        company=company, user=user, role=role, status=CompanyMembershipStatus.ACTIVE
    )


class DashboardViewTestCase(TestCase):
    """
    Integration test suite for `GET /reports/dashboard` (BE-048).
    """

    def setUp(self):
        self.client = APIClient()

        self.member_user = User.objects.create_user(
            email="alice@company1.com", name="Alice Member", password="StrongPassword123!"
        )
        self.member_token = str(CompanyUserAccessToken.for_user(self.member_user))

        self.company1 = Company.objects.create(name="Studio One", status=CompanyStatus.ACTIVE)
        make_full_access_membership(self.company1, self.member_user)

        self.client1 = Client.objects.create(company=self.company1, name="Client One")
        Project.objects.create(company=self.company1, client=self.client1, name="Kitchen Remodel")

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.member_token}")

    def test_unauthenticated_fails_401(self):
        self.client.credentials()
        response = self.client.get("/reports/dashboard")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_dashboard(self):
        response = self.client.get("/reports/dashboard")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()["data"]
        self.assertEqual(data["kpis"]["totalProjects"], 1)
        self.assertEqual(len(data["recentProjects"]), 1)
        self.assertEqual(data["recentProjects"][0]["name"], "Kitchen Remodel")


class DashboardFinancialAccessTestCase(TestCase):
    """
    BE-068 regression: `report.view` alone must never expose financial
    dashboard data -- the backend omits it at the source, not just hides
    it in the UI.
    """

    def setUp(self):
        self.client = APIClient()

        self.company1 = Company.objects.create(name="Studio One", status=CompanyStatus.ACTIVE)
        self.company2 = Company.objects.create(name="Studio Two", status=CompanyStatus.ACTIVE)
        self.client1 = Client.objects.create(company=self.company1, name="Client One")
        self.project1 = Project.objects.create(company=self.company1, client=self.client1, name="Kitchen Remodel")

        # Real financial activity so the assertions prove absence of real
        # data, not merely the absence of an already-empty section.
        invoice = InvoiceService.create_invoice(
            project=self.project1,
            items=[{"description": "Design Fee", "quantity": Decimal("1.00"), "rate": Decimal("5000.00")}],
        )
        InvoiceService.send_invoice(invoice)
        invoice.refresh_from_db()
        PaymentService.create_payment(invoice=invoice, payment_date="2026-09-01", amount=Decimal("2000.00"))
        self.invoice = invoice

        self.full_access_user = User.objects.create_user(
            email="full@company1.com", name="Full Access", password="StrongPassword123!"
        )
        make_full_access_membership(self.company1, self.full_access_user)
        self.full_access_token = str(CompanyUserAccessToken.for_user(self.full_access_user))

        self.view_only_user = User.objects.create_user(
            email="viewonly@company1.com", name="View Only", password="StrongPassword123!"
        )
        make_report_view_only_membership(self.company1, self.view_only_user)
        self.view_only_token = str(CompanyUserAccessToken.for_user(self.view_only_user))

        self.no_access_user = User.objects.create_user(
            email="noaccess@company1.com", name="No Access", password="StrongPassword123!"
        )
        CompanyMembership.objects.create(
            company=self.company1, user=self.no_access_user, role=None, status=CompanyMembershipStatus.ACTIVE
        )
        self.no_access_token = str(CompanyUserAccessToken.for_user(self.no_access_user))

    # 2. user without report.view -> 403
    def test_user_without_report_view_gets_403(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.no_access_token}")
        response = self.client.get("/reports/dashboard")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    # 3. report.view only user -> 200
    def test_report_view_only_user_gets_200(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.view_only_token}")
        response = self.client.get("/reports/dashboard")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    # 4. report.view-only response contains operational data
    def test_report_view_only_response_contains_operational_data(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.view_only_token}")
        data = self.client.get("/reports/dashboard").json()["data"]

        self.assertEqual(data["kpis"]["totalProjects"], 1)
        self.assertEqual(data["kpis"]["activeProjects"], 1)
        self.assertEqual(len(data["recentProjects"]), 1)
        self.assertEqual(data["recentProjects"][0]["name"], "Kitchen Remodel")
        self.assertFalse(data["canViewFinancials"])

    # 5. report.view-only response DOES NOT expose financial values
    def test_report_view_only_response_omits_every_financial_field(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.view_only_token}")
        data = self.client.get("/reports/dashboard").json()["data"]

        for key in ("totalBilledRevenue", "totalReceived", "pendingAmount", "totalExpenses", "netProfitLoss"):
            self.assertNotIn(key, data["kpis"], f"{key} must not appear in kpis for a report.view-only caller")
        # recentActivities is gated too -- its beforeState/afterState audit
        # snapshots leak real financial figures for an invoice/payment
        # entry (found during implementation, not assumed operational).
        for section in (
            "pendingPayments", "overdueInvoices", "recentExpenses", "projectProfitability", "recentActivities",
        ):
            self.assertNotIn(section, data, f"{section} must not appear in the response for a report.view-only caller")

        # Belt-and-braces: no real dollar amount anywhere in the raw response text.
        raw = self.client.get("/reports/dashboard").content.decode()
        self.assertNotIn("5000.00", raw)
        self.assertNotIn("2000.00", raw)

    # 6/7. user with report.view + report.financial_access -> full response, correct KPIs
    def test_full_access_user_gets_complete_response_with_correct_financial_kpis(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.full_access_token}")
        data = self.client.get("/reports/dashboard").json()["data"]

        self.assertTrue(data["canViewFinancials"])
        self.assertEqual(data["kpis"]["totalBilledRevenue"], "5000.00")
        self.assertEqual(data["kpis"]["totalReceived"], "2000.00")
        self.assertEqual(data["kpis"]["pendingAmount"], "3000.00")
        self.assertIn("pendingPayments", data)
        self.assertIn("overdueInvoices", data)
        self.assertIn("recentExpenses", data)
        self.assertIn("projectProfitability", data)
        self.assertIn("recentActivities", data)

    # 8. projectProfitability unavailable to unauthorized financial viewer
    def test_project_profitability_unavailable_without_financial_access(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.view_only_token}")
        data = self.client.get("/reports/dashboard").json()["data"]
        self.assertNotIn("projectProfitability", data)

    # 9. pending/payment/invoice financial data protected
    def test_pending_payments_and_overdue_invoices_protected(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.view_only_token}")
        data = self.client.get("/reports/dashboard").json()["data"]
        self.assertNotIn("pendingPayments", data)
        self.assertNotIn("overdueInvoices", data)

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.full_access_token}")
        data = self.client.get("/reports/dashboard").json()["data"]
        self.assertEqual(len(data["pendingPayments"]), 1)
        self.assertEqual(data["pendingPayments"][0]["id"], str(self.invoice.id))

    # 10. tenant isolation unchanged
    def test_tenant_isolation_unchanged(self):
        other_client = Client.objects.create(company=self.company2, name="Other Client")
        Project.objects.create(company=self.company2, client=other_client, name="Other Project")

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.full_access_token}")
        data = self.client.get("/reports/dashboard").json()["data"]

        project_names = {p["name"] for p in data["recentProjects"]}
        self.assertNotIn("Other Project", project_names)
        self.assertEqual(data["kpis"]["totalProjects"], 1)

    # 11. platform-admin behavior follows current convention (standing bypass)
    def test_platform_admin_gets_full_financial_response(self):
        superadmin = User.objects.create_superuser(
            email="superadmin@example.com", name="Super Admin", password="StrongPassword123!"
        )
        token = str(PlatformAdminAccessToken.for_user(superadmin))
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

        response = self.client.get(f"/reports/dashboard?companyId={self.company1.id}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()["data"]
        self.assertTrue(data["canViewFinancials"])
        self.assertIn("totalBilledRevenue", data["kpis"])
        self.assertIn("projectProfitability", data)

    def test_platform_admin_without_company_id_returns_400(self):
        superadmin = User.objects.create_superuser(
            email="superadmin2@example.com", name="Super Admin 2", password="StrongPassword123!"
        )
        token = str(PlatformAdminAccessToken.for_user(superadmin))
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

        response = self.client.get("/reports/dashboard")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # 12. no role-name authorization -- a role named "Owner"/"Admin" without
    # report.financial_access is still restricted; the check is the
    # permission code, never the name.
    def test_role_display_name_never_grants_financial_access(self):
        impostor_role = Role.objects.create(company=self.company1, name="Owner", is_active=True)
        RolePermission.objects.create(
            role=impostor_role, permission=Permission.objects.get(code="report.view")
        )
        impostor_user = User.objects.create_user(
            email="impostor@company1.com", name="Impostor Owner", password="StrongPassword123!"
        )
        CompanyMembership.objects.create(
            company=self.company1, user=impostor_user, role=impostor_role, status=CompanyMembershipStatus.ACTIVE
        )
        token = str(CompanyUserAccessToken.for_user(impostor_user))
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

        data = self.client.get("/reports/dashboard").json()["data"]
        self.assertFalse(data["canViewFinancials"])
        self.assertNotIn("totalBilledRevenue", data["kpis"])
