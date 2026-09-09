from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APIClient

from apps.authentication.tests.base import ThrottleIsolatedTestCase
from apps.authentication.tokens import CompanyUserAccessToken
from apps.company.models import Company, CompanyStatus
from apps.users.models import CompanyMembership, CompanyMembershipStatus, Role

User = get_user_model()


class MyMembershipsViewTestCase(ThrottleIsolatedTestCase):
    """
    Integration tests for `GET /auth/memberships` (BE-053) -- the
    workspace-switching endpoint flagged as missing during the frontend
    Milestone 1 build.
    """

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email="multi@example.com", name="Multi Company User", password="StrongPassword123!"
        )
        self.token = str(CompanyUserAccessToken.for_user(self.user))

        self.company1 = Company.objects.create(name="Studio One", status=CompanyStatus.ACTIVE)
        self.company2 = Company.objects.create(name="Studio Two", status=CompanyStatus.ACTIVE)
        self.role = Role.objects.create(company=self.company1, name="Accountant", is_active=True)

    def test_requires_authentication(self):
        response = self.client.get("/auth/memberships")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_zero_memberships_returns_empty_list_not_403(self):
        """
        Unlike every other company-scoped endpoint, a user with zero
        memberships must not be rejected here -- this endpoint's entire
        purpose is to work for that exact case (BE-053 is exempted from
        tenant resolution).
        """
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token}")
        response = self.client.get("/auth/memberships")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["data"], [])

    def test_lists_only_active_memberships_across_companies(self):
        CompanyMembership.objects.create(
            company=self.company1,
            user=self.user,
            role=self.role,
            status=CompanyMembershipStatus.ACTIVE,
        )
        CompanyMembership.objects.create(
            company=self.company2, user=self.user, status=CompanyMembershipStatus.REVOKED
        )

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token}")
        response = self.client.get("/auth/memberships")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()["data"]
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["companyId"], str(self.company1.id))
        self.assertEqual(data[0]["companyName"], "Studio One")
        self.assertEqual(data[0]["roleName"], "Accountant")
        self.assertEqual(set(data[0].keys()), {"companyId", "companyName", "status", "roleName"})

    def test_multi_company_user_sees_every_active_company(self):
        CompanyMembership.objects.create(
            company=self.company1, user=self.user, status=CompanyMembershipStatus.ACTIVE
        )
        CompanyMembership.objects.create(
            company=self.company2, user=self.user, status=CompanyMembershipStatus.ACTIVE
        )

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token}")
        response = self.client.get("/auth/memberships")

        company_ids = {row["companyId"] for row in response.json()["data"]}
        self.assertEqual(company_ids, {str(self.company1.id), str(self.company2.id)})

    def test_does_not_leak_other_users_memberships(self):
        other_user = User.objects.create_user(
            email="other@example.com", name="Other", password="StrongPassword123!"
        )
        CompanyMembership.objects.create(
            company=self.company1, user=other_user, status=CompanyMembershipStatus.ACTIVE
        )

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token}")
        response = self.client.get("/auth/memberships")
        self.assertEqual(response.json()["data"], [])
