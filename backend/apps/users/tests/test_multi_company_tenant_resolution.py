from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from apps.authentication.tokens import CompanyUserAccessToken
from apps.company.models import Company, CompanyStatus
from apps.users.models import CompanyMembership, CompanyMembershipStatus, Role

User = get_user_model()


class MultiCompanyRoleTenantResolutionTestCase(TestCase):
    """
    BE-021: RoleViewSet/RolePermission previously re-derived tenant scope
    from request.user.memberships instead of trusting request.company_id
    (already resolved, validated, and disambiguated by
    TenantJWTAuthentication). These tests exercise the real /roles
    endpoints — not the tenant_info_support.py diagnostic view BE-017 used
    — with a genuinely multi-membership user, the exact case the duplicate
    resolution logic got wrong.
    """

    def setUp(self):
        self.client = APIClient()

        self.company1 = Company.objects.create(name="Alpha Studio", status=CompanyStatus.ACTIVE)
        self.company2 = Company.objects.create(name="Beta Studio", status=CompanyStatus.ACTIVE)

        self.multi_user = User.objects.create_user(
            email="multi@example.com", name="Multi Co", password="StrongPassword123!"
        )
        CompanyMembership.objects.create(
            company=self.company1, user=self.multi_user, status=CompanyMembershipStatus.ACTIVE
        )
        CompanyMembership.objects.create(
            company=self.company2, user=self.multi_user, status=CompanyMembershipStatus.ACTIVE
        )
        self.multi_token = str(CompanyUserAccessToken.for_user(self.multi_user))

        self.role_c1 = Role.objects.create(company=self.company1, name="C1 Role", is_active=True)
        self.role_c1_second = Role.objects.create(company=self.company1, name="C1 Second Role", is_active=True)
        self.role_c2 = Role.objects.create(company=self.company2, name="C2 Role", is_active=True)

    def test_multi_company_member_lists_roles_scoped_to_explicit_company_id(self):
        """
        Explicit companyId=company1 must return only company1's roles —
        never company2's, even though the caller is an active member of both.
        """
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.multi_token}")
        response = self.client.get(f"/roles?companyId={self.company1.id}")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        names = [r["name"] for r in response.json()["data"]]
        self.assertEqual(set(names), {"C1 Role", "C1 Second Role"})

    def test_multi_company_member_lists_roles_for_the_other_company(self):
        """
        Same user, same session shape, just companyId=company2 this time —
        proves the resolution isn't accidentally sticky/cached to one company.
        """
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.multi_token}")
        response = self.client.get(f"/roles?companyId={self.company2.id}")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        names = [r["name"] for r in response.json()["data"]]
        self.assertEqual(names, ["C2 Role"])

    def test_multi_company_member_without_company_id_is_rejected_as_ambiguous(self):
        """
        Per Tenant.md §4, a company-scoped resource never supports a "list
        across all my companies" mode for a non-admin — that ambiguity must
        be resolved by supplying companyId. This documents the intended
        behavior (TenantJWTAuthentication rejects before the view even
        runs), not a regression: the view has no "list across all my
        companies" fallback left to reach.
        """
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.multi_token}")
        response = self.client.get("/roles")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_multi_company_member_creates_role_in_the_specified_company(self):
        """
        Creation must land in whichever of the caller's real companies they
        specify — driven by request.company_id, not a re-derived membership
        lookup that could pick the wrong one.
        """
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.multi_token}")
        response = self.client.post(
            "/roles",
            {"name": "New Multi Role", "companyId": str(self.company2.id)},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.json()["data"]["companyId"], str(self.company2.id))
        role = Role.objects.get(name="New Multi Role")
        self.assertEqual(role.company_id, self.company2.id)

    def test_multi_company_member_retrieves_role_with_matching_company_context(self):
        """
        Retrieving a Company 2 role while resolved into a Company 2 context
        (via companyId) succeeds.
        """
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.multi_token}")
        response = self.client.get(f"/roles/{self.role_c2.id}?companyId={self.company2.id}")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["data"]["id"], str(self.role_c2.id))

    def test_multi_company_member_retrieve_fails_when_company_context_is_the_wrong_one(self):
        """
        The caller is a legitimate active member of BOTH companies, but this
        specific request is resolved into the Company 1 context (companyId=
        company1) while asking for a Company 2 role by ID. Even a genuine
        multi-company member must not reach across the company context a
        single request was resolved into — request.company_id is a
        per-request boundary, not a per-user allowlist. 404, not 403 — this
        is the same anti-enumeration boundary as a real cross-tenant IDOR
        attempt (ObjectPermission404Mixin), just reached by a multi-company
        member instead of a single-company one.
        """
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.multi_token}")
        response = self.client.get(f"/roles/{self.role_c2.id}?companyId={self.company1.id}")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_multi_company_member_conflicting_query_and_body_company_id_rejected(self):
        """
        Query string says Company 1, request body's companyId says Company 2
        — both individually valid memberships for this user, but they
        disagree. TenantJWTAuthentication resolves request.company_id from
        the query value (Company 1); the view must reject rather than
        silently trust the body's differing value as the create target.
        """
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.multi_token}")
        response = self.client.post(
            f"/roles?companyId={self.company1.id}",
            {"name": "Conflicting Role", "companyId": str(self.company2.id)},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertFalse(Role.objects.filter(name="Conflicting Role").exists())
