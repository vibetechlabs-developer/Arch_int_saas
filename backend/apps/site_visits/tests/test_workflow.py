from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.authentication.tokens import CompanyUserAccessToken
from apps.clients.models import Client
from apps.common.test_utils import make_full_access_membership
from apps.company.models import Company, CompanyStatus
from apps.leads.models import Lead
from apps.leads.services import LeadService
from apps.projects.models import Project
from apps.site_visits.models import SiteVisit
from apps.users.models import CompanyMembership, CompanyMembershipStatus
from apps.users.services import RoleService

User = get_user_model()


class SiteVisitReportEndpointTestCase(TestCase):
    """Integration tests for POST /site-visits/{id}/report (BE-062)."""

    def setUp(self):
        self.client = APIClient()

        self.member_user = User.objects.create_user(
            email="alice@company1.com", name="Alice Member", password="StrongPassword123!"
        )
        self.member_token = str(CompanyUserAccessToken.for_user(self.member_user))

        self.company1 = Company.objects.create(name="Studio One", status=CompanyStatus.ACTIVE)
        make_full_access_membership(self.company1, self.member_user)

        self.client_obj = Client.objects.create(company=self.company1, name="Jane Client")
        self.project = Project.objects.create(company=self.company1, client=self.client_obj, name="Kitchen Remodel")
        self.lead = Lead.objects.create(company=self.company1, name="Jane Prospect")

    def _url(self, visit_id):
        return f"/site-visits/{visit_id}/report"

    def test_submit_report_against_project_marks_completed(self):
        visit = SiteVisit.objects.create(
            company=self.company1, project=self.project, visit_date=timezone.now() + timedelta(days=1)
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.member_token}")
        response = self.client.post(self._url(visit.id), {}, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()["data"]
        self.assertTrue(data["isCompleted"])
        self.assertIsNotNone(data["reportSubmittedAt"])

    def test_submit_report_is_idempotent_via_api(self):
        visit = SiteVisit.objects.create(
            company=self.company1, project=self.project, visit_date=timezone.now() + timedelta(days=1)
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.member_token}")
        first_response = self.client.post(self._url(visit.id), {}, format="json")
        second_response = self.client.post(self._url(visit.id), {}, format="json")

        self.assertEqual(first_response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            first_response.json()["data"]["reportSubmittedAt"],
            second_response.json()["data"]["reportSubmittedAt"],
        )

    def test_submit_report_with_create_project_against_converted_lead(self):
        converted = LeadService.convert_lead(self.lead.id)
        visit = SiteVisit.objects.create(
            company=self.company1, lead=self.lead, visit_date=timezone.now() + timedelta(days=1)
        )
        visit.client_id = converted.converted_client_id
        visit.save()

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.member_token}")
        response = self.client.post(
            self._url(visit.id), {"createProject": True, "projectName": "From Site Visit"}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()["data"]
        self.assertIsNotNone(data["projectId"])
        self.assertEqual(data["projectName"], "From Site Visit")

    def test_submit_report_create_project_without_client_returns_409(self):
        visit = SiteVisit.objects.create(
            company=self.company1, lead=self.lead, visit_date=timezone.now() + timedelta(days=1)
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.member_token}")
        response = self.client.post(self._url(visit.id), {"createProject": True}, format="json")
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)

    def test_cross_tenant_site_visit_report_returns_404(self):
        other_company = Company.objects.create(name="Studio Two", status=CompanyStatus.ACTIVE)
        other_client = Client.objects.create(company=other_company, name="Other Client")
        other_project = Project.objects.create(company=other_company, client=other_client, name="Other Project")
        other_visit = SiteVisit.objects.create(
            company=other_company, project=other_project, visit_date=timezone.now() + timedelta(days=1)
        )

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.member_token}")
        response = self.client.post(self._url(other_visit.id), {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class SiteVisitGranularRbacTestCase(TestCase):
    """
    RBAC granularity tests (BE-062): a "Sales / CRM User"-style role
    (view/create/edit/report, no delete) can submit reports but is
    forbidden from deleting site visits — verifying `site_visit.report`
    is a distinct, independently-enforced permission code from
    `site_visit.delete`, mirroring apps.leads.tests.test_workflow's
    LeadGranularRbacTestCase.
    """

    def setUp(self):
        self.client = APIClient()

        self.company = Company.objects.create(name="Studio One", status=CompanyStatus.ACTIVE)

        self.sales_role = RoleService.create_role(company_id=self.company.id, name="Sales Rep Role")
        RoleService.assign_permissions(
            role_id=self.sales_role.id,
            codes=["site_visit.view", "site_visit.create", "site_visit.edit", "site_visit.report"],
        )

        self.sales_user = User.objects.create_user(
            email="sales@company1.com", name="Sales Rep", password="StrongPassword123!"
        )
        CompanyMembership.objects.create(
            company=self.company,
            user=self.sales_user,
            role=self.sales_role,
            status=CompanyMembershipStatus.ACTIVE,
        )
        self.sales_token = str(CompanyUserAccessToken.for_user(self.sales_user))

        self.client_obj = Client.objects.create(company=self.company, name="Jane Client")
        self.project = Project.objects.create(company=self.company, client=self.client_obj, name="Kitchen Remodel")
        self.visit = SiteVisit.objects.create(
            company=self.company, project=self.project, visit_date=timezone.now() + timedelta(days=1)
        )

    def test_sales_role_can_submit_report(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.sales_token}")
        response = self.client.post(f"/site-visits/{self.visit.id}/report", {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_sales_role_cannot_delete(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.sales_token}")
        response = self.client.delete(f"/site-visits/{self.visit.id}")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        self.visit.refresh_from_db()
        self.assertFalse(self.visit.is_deleted)

    def test_role_without_report_code_cannot_submit_report(self):
        no_report_role = RoleService.create_role(company_id=self.company.id, name="View Only Role")
        RoleService.assign_permissions(role_id=no_report_role.id, codes=["site_visit.view", "site_visit.edit"])

        limited_user = User.objects.create_user(
            email="limited@company1.com", name="Limited User", password="StrongPassword123!"
        )
        CompanyMembership.objects.create(
            company=self.company, user=limited_user, role=no_report_role, status=CompanyMembershipStatus.ACTIVE
        )
        limited_token = str(CompanyUserAccessToken.for_user(limited_user))

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {limited_token}")
        response = self.client.post(f"/site-visits/{self.visit.id}/report", {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class SeededDefaultRoleSiteVisitPermissionTestCase(TestCase):
    """
    Verifies the DEFAULT_ROLE_PERMISSIONS extension for Admin/Sales-CRM-User
    (BE-062) — new companies seeded after this migration get the
    site_visit.* codes on those roles automatically via
    RoleService.seed_default_roles_for_company.
    """

    def setUp(self):
        self.company = Company.objects.create(name="Fresh Co", status=CompanyStatus.ACTIVE)
        RoleService.seed_default_roles_for_company(self.company)

    def test_admin_role_gets_all_site_visit_codes(self):
        from apps.users.models import Role
        from apps.users.repositories import PermissionRepository

        admin_role = Role.objects.get(company=self.company, name="Admin")
        codes = PermissionRepository.codes_for_role(admin_role.id)
        for code in ("site_visit.view", "site_visit.create", "site_visit.edit", "site_visit.delete", "site_visit.report"):
            self.assertIn(code, codes)

    def test_sales_role_gets_site_visit_codes_but_not_delete(self):
        from apps.users.models import Role
        from apps.users.repositories import PermissionRepository

        sales_role = Role.objects.get(company=self.company, name="Sales / CRM User")
        codes = PermissionRepository.codes_for_role(sales_role.id)
        for code in ("site_visit.view", "site_visit.create", "site_visit.edit", "site_visit.report"):
            self.assertIn(code, codes)
        self.assertNotIn("site_visit.delete", codes)
