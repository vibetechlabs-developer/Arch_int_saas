from types import SimpleNamespace

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from apps.company.models import Company, CompanyStatus
from apps.projects.models import Project
from apps.clients.models import Client
from apps.site_visits.models import SiteVisit
from apps.site_visits.permissions import SiteVisitPermission

User = get_user_model()


def make_request(user, company_id=None, is_platform_admin_token=False):
    """Mirrors apps.leads.tests.test_permissions.make_request exactly."""
    auth = {"token_type": "platform_admin"} if is_platform_admin_token else {}
    return SimpleNamespace(user=user, auth=auth, company_id=company_id)


class SiteVisitPermissionTestCase(TestCase):
    """
    Unit-level test suite for SiteVisitPermission (BE-062), mirroring
    apps.leads.tests.test_permissions.LeadPermissionTestCase.
    """

    def setUp(self):
        self.permission = SiteVisitPermission()
        self.company = Company.objects.create(name="Company One", status=CompanyStatus.ACTIVE)
        self.other_company = Company.objects.create(name="Company Two", status=CompanyStatus.ACTIVE)

        self.company_user = User.objects.create_user(
            email="user@company-one.com", name="Company User", password="StrongPassword123!"
        )
        self.superadmin = User.objects.create_superuser(
            email="admin@platform.com", name="Super Admin", password="StrongPassword123!"
        )

        client_obj = Client.objects.create(company=self.company, name="Jane Doe")
        project = Project.objects.create(company=self.company, client=client_obj, name="Kitchen Remodel")
        self.site_visit = SiteVisit.objects.create(company=self.company, project=project, visit_date=timezone.now())

    def test_unauthenticated_user_denied(self):
        anon = SimpleNamespace(is_authenticated=False)
        request = make_request(user=anon)
        self.assertFalse(self.permission.has_permission(request, view=None))

    def test_company_user_with_resolved_company_id_but_no_membership_or_code_denied(self):
        request = make_request(user=self.company_user, company_id=self.company.id)
        self.assertFalse(self.permission.has_permission(request, view=None))

    def test_company_user_with_no_resolved_company_id_denied(self):
        request = make_request(user=self.company_user, company_id=None)
        self.assertFalse(self.permission.has_permission(request, view=None))

    def test_platform_admin_superuser_flag_allowed(self):
        request = make_request(user=self.superadmin, company_id=None)
        self.assertTrue(self.permission.has_permission(request, view=None))

    def test_platform_admin_token_claim_allowed(self):
        request = make_request(user=self.company_user, company_id=None, is_platform_admin_token=True)
        self.assertTrue(self.permission.has_permission(request, view=None))

    def test_object_permission_same_tenant_allowed(self):
        request = make_request(user=self.company_user, company_id=self.company.id)
        self.assertTrue(self.permission.has_object_permission(request, view=None, obj=self.site_visit))

    def test_object_permission_cross_tenant_denied(self):
        request = make_request(user=self.company_user, company_id=self.other_company.id)
        self.assertFalse(self.permission.has_object_permission(request, view=None, obj=self.site_visit))

    def test_object_permission_platform_admin_bypasses_tenant_check(self):
        request = make_request(user=self.superadmin, company_id=None)
        self.assertTrue(self.permission.has_object_permission(request, view=None, obj=self.site_visit))
