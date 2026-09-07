from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from apps.authentication.tokens import CompanyUserAccessToken
from apps.common.test_utils import make_full_access_membership
from apps.company.models import Company, CompanyStatus
from apps.users.models import CompanyMembership, CompanyMembershipStatus

User = get_user_model()


class MultiCompanyCompanyTenantResolutionTestCase(TestCase):
    """
    BE-021: IsPlatformAdminOrCompanyAccess.has_object_permission previously
    re-derived tenant scope from request.user.memberships instead of
    trusting request.company_id (already resolved and validated by
    TenantJWTAuthentication). These tests exercise the real /companies
    endpoints with a genuinely multi-membership user.
    """

    def setUp(self):
        self.client = APIClient()

        self.company1 = Company.objects.create(name="Alpha Studio", status=CompanyStatus.ACTIVE)
        self.company2 = Company.objects.create(name="Beta Studio", status=CompanyStatus.ACTIVE)

        self.multi_user = User.objects.create_user(
            email="multi@example.com", name="Multi Co", password="StrongPassword123!"
        )
        make_full_access_membership(self.company1, self.multi_user)
        make_full_access_membership(self.company2, self.multi_user)
        self.multi_token = str(CompanyUserAccessToken.for_user(self.multi_user))

    def test_multi_company_member_retrieves_first_company_via_explicit_company_id(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.multi_token}")
        response = self.client.get(f"/companies/{self.company1.id}?companyId={self.company1.id}")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["data"]["id"], str(self.company1.id))

    def test_multi_company_member_retrieves_second_company_via_explicit_company_id(self):
        """
        Same user, same test class setup, just the other company this time —
        proves resolution isn't sticky to whichever company happened to be
        checked first in a membership queryset.
        """
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.multi_token}")
        response = self.client.get(f"/companies/{self.company2.id}?companyId={self.company2.id}")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["data"]["id"], str(self.company2.id))

    def test_multi_company_member_without_company_id_is_rejected_as_ambiguous(self):
        """
        Documents intended TenantJWTAuthentication behavior for a request
        with no path-independent way to disambiguate — not a regression.
        """
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.multi_token}")
        response = self.client.get(f"/companies/{self.company1.id}")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_multi_company_member_company_id_mismatch_with_url_pk_returns_404(self):
        """
        The caller is a legitimate active member of BOTH companies, but this
        request is resolved into the Company 1 context (companyId=company1)
        while the URL asks for Company 2 by ID. CompanyViewSet has
        ObjectPermission404Mixin, so a per-request context mismatch here is
        404 (anti-enumeration), unlike Role's still-open 403 (BE-018).
        """
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.multi_token}")
        response = self.client.get(f"/companies/{self.company2.id}?companyId={self.company1.id}")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_multi_company_member_updates_each_company_within_its_own_context(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.multi_token}")

        resp1 = self.client.patch(
            f"/companies/{self.company1.id}?companyId={self.company1.id}",
            {"name": "Alpha Studio Renamed"},
            format="json",
        )
        self.assertEqual(resp1.status_code, status.HTTP_200_OK)
        self.assertEqual(resp1.json()["data"]["name"], "Alpha Studio Renamed")

        resp2 = self.client.patch(
            f"/companies/{self.company2.id}?companyId={self.company2.id}",
            {"name": "Beta Studio Renamed"},
            format="json",
        )
        self.assertEqual(resp2.status_code, status.HTTP_200_OK)
        self.assertEqual(resp2.json()["data"]["name"], "Beta Studio Renamed")
