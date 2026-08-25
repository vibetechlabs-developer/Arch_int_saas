import uuid
from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from apps.authentication.tokens import CompanyUserAccessToken, PlatformAdminAccessToken
from apps.company.models import Company, CompanyStatus
from apps.users.models import CompanyMembership, CompanyMembershipStatus

User = get_user_model()


class CompanyViewSetTestCase(TestCase):
    """
    Integration test suite for Company CRUD endpoints (BE-011).
    """

    def setUp(self):
        self.client = APIClient()

        # 1. Platform Super Admin User
        self.superadmin = User.objects.create_superuser(
            email="superadmin@example.com",
            name="Super Admin",
            password="StrongPassword123!",
        )
        self.superadmin_token = str(PlatformAdminAccessToken.for_user(self.superadmin))

        # 2. Company Member User
        self.member_user = User.objects.create_user(
            email="member@example.com",
            name="Alice Member",
            password="StrongPassword123!",
        )
        self.member_token = str(CompanyUserAccessToken.for_user(self.member_user))

        # 3. Non-Member User
        self.other_user = User.objects.create_user(
            email="other@example.com",
            name="Bob Other",
            password="StrongPassword123!",
        )
        self.other_token = str(CompanyUserAccessToken.for_user(self.other_user))

        # 4. Companies
        self.company1 = Company.objects.create(
            name="Alpha Design Studio",
            status=CompanyStatus.ACTIVE,
            currency="INR",
            gst_number="27AAAAA1111A1Z1",
            settings={"numbering": {"invoicePrefix": "ALPHA-"}},
        )
        self.company2 = Company.objects.create(
            name="Beta Architecture",
            status=CompanyStatus.TRIAL,
            currency="USD",
        )

        # 5. Memberships
        CompanyMembership.objects.create(
            company=self.company1,
            user=self.member_user,
            status=CompanyMembershipStatus.ACTIVE,
        )

    def test_unauthenticated_requests_fail_401(self):
        """
        Verify that all company endpoints reject unauthenticated requests with 401.
        """
        resp_list = self.client.get("/companies")
        self.assertEqual(resp_list.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(resp_list.json()["error"]["code"], "AUTHENTICATION_ERROR")

        resp_create = self.client.post("/companies", {"name": "New Co"})
        self.assertEqual(resp_create.status_code, status.HTTP_401_UNAUTHORIZED)

        resp_detail = self.client.get(f"/companies/{self.company1.id}")
        self.assertEqual(resp_detail.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_company_as_platform_admin_success(self):
        """
        Verify Platform Admin can create a new company (201 Created).
        """
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.superadmin_token}")
        payload = {
            "name": "Zenith Studios",
            "currency": "INR",
            "gstNumber": "27ZZZZZ9999Z1Z9",
            "settings": {"paymentTerms": {"defaultDays": 45}},
        }
        response = self.client.post("/companies", payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["data"]["name"], "Zenith Studios")
        self.assertEqual(data["data"]["currency"], "INR")
        self.assertEqual(data["data"]["gstNumber"], "27ZZZZZ9999Z1Z9")
        self.assertEqual(data["data"]["status"], "trial")
        self.assertEqual(data["data"]["settings"]["paymentTerms"]["defaultDays"], 45)
        self.assertIn("requestId", data)

    def test_create_company_as_regular_user_fails_403(self):
        """
        Verify regular authenticated user cannot create companies (403 Permission Error).
        """
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.member_token}")
        response = self.client.post("/companies", {"name": "Unauthorized Co"}, format="json")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.json()["error"]["code"], "PERMISSION_ERROR")

    def test_create_company_validation_error_400(self):
        """
        Verify company creation validates required fields and formats (400 Validation Error).
        """
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.superadmin_token}")
        response = self.client.post("/companies", {"name": "   "}, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        data = response.json()
        self.assertFalse(data["success"])
        self.assertEqual(data["error"]["code"], "VALIDATION_ERROR")
        self.assertTrue(any(d["field"] == "name" for d in data["error"]["details"]))

    def test_list_companies_as_platform_admin(self):
        """
        Verify Platform Admin can list companies with pagination (200 OK).
        """
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.superadmin_token}")
        response = self.client.get("/companies")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertIn("pagination", data)
        self.assertGreaterEqual(len(data["data"]), 2)
        self.assertEqual(data["pagination"]["page"], 1)

    def test_list_companies_as_regular_user_fails_403(self):
        """
        Verify regular user cannot list all companies (403 Permission Error).
        """
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.member_token}")
        response = self.client.get("/companies")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.json()["error"]["code"], "PERMISSION_ERROR")

    def test_list_companies_filtering_and_search(self):
        """
        Verify status filtering and name search on companies list.
        """
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.superadmin_token}")

        # Filter by status=active
        resp_active = self.client.get("/companies?status=active")
        self.assertEqual(resp_active.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp_active.json()["data"]), 1)
        self.assertEqual(resp_active.json()["data"][0]["name"], "Alpha Design Studio")

        # Search by keyword
        resp_search = self.client.get("/companies?search=Beta")
        self.assertEqual(resp_search.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp_search.json()["data"]), 1)
        self.assertEqual(resp_search.json()["data"][0]["name"], "Beta Architecture")

    def test_get_company_detail_as_platform_admin(self):
        """
        Verify Platform Admin can retrieve any company detail by UUID.
        """
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.superadmin_token}")
        response = self.client.get(f"/companies/{self.company1.id}")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data["data"]["id"], str(self.company1.id))
        self.assertEqual(data["data"]["name"], "Alpha Design Studio")

    def test_get_company_detail_as_member(self):
        """
        Verify company member can retrieve their own company detail.
        """
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.member_token}")
        response = self.client.get(f"/companies/{self.company1.id}")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data["data"]["id"], str(self.company1.id))
        self.assertEqual(data["data"]["name"], "Alpha Design Studio")

    def test_get_company_detail_as_user_with_no_company_membership_fails_403(self):
        """
        A user with ZERO active company memberships anywhere is rejected by
        TenantJWTAuthentication itself (see apps/authentication/
        authentication.py's "no active company membership" branch) before
        the view or its object-level permission check are ever reached.
        This 403 is identical regardless of which company ID (real or
        fake) was requested, so it reveals nothing company-specific — it is
        NOT the Error_Handling.md §5 enumeration case (which is about the
        response DIFFERING based on whether a specific ID is real), so it
        correctly stays 403, distinct from the genuine cross-tenant case
        below.
        """
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.other_token}")
        response = self.client.get(f"/companies/{self.company1.id}")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.json()["error"]["code"], "PERMISSION_ERROR")

    def test_patch_company_as_user_with_no_company_membership_fails_403(self):
        """
        Same boundary as above (TenantJWTAuthentication, not the view's
        object-level check), exercised via PATCH.
        """
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.other_token}")
        response = self.client.patch(
            f"/companies/{self.company1.id}",
            {"name": "Hostile Rename Attempt"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.json()["error"]["code"], "PERMISSION_ERROR")

        # The company must be entirely unaffected by the rejected attempt.
        self.company1.refresh_from_db()
        self.assertEqual(self.company1.name, "Alpha Design Studio")

    def test_get_company_detail_as_member_of_different_company_returns_404(self):
        """
        BE-018 (Decision 1 — the genuine cross-tenant case): a user who IS
        an active member of Company 1 gets 404, not 403, when probing
        Company 2 (which they do NOT belong to). Unlike the no-membership
        case above, this request DOES pass tenant resolution (the caller
        has exactly one active membership, so TenantJWTAuthentication
        resolves request.company_id to Company 1 without error) and reaches
        the view's object-level permission check for Company 2 specifically
        — this is the real Error_Handling.md §5 enumeration scenario, fixed
        by ObjectPermission404Mixin (apps/common/views.py).
        """
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.member_token}")
        response = self.client.get(f"/companies/{self.company2.id}")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.json()["error"]["code"], "NOT_FOUND")

    def test_patch_company_as_member_of_different_company_returns_404(self):
        """
        PATCH equivalent of the test above — the genuine cross-tenant
        object-level case, via the mutating verb.
        """
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.member_token}")
        response = self.client.patch(
            f"/companies/{self.company2.id}",
            {"name": "Hostile Rename Attempt"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.json()["error"]["code"], "NOT_FOUND")

        self.company2.refresh_from_db()
        self.assertEqual(self.company2.name, "Beta Architecture")

    def test_update_company_validation_error_400(self):
        """
        BE-018: PATCH with a blank name is rejected by CompanyUpdateSerializer
        with the standard 400 VALIDATION_ERROR envelope — previously only
        exercised on create, never on update.
        """
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.superadmin_token}")
        response = self.client.patch(
            f"/companies/{self.company1.id}",
            {"name": "   "},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        data = response.json()
        self.assertFalse(data["success"])
        self.assertEqual(data["error"]["code"], "VALIDATION_ERROR")
        self.assertTrue(any(d["field"] == "name" for d in data["error"]["details"]))

        # Original name must be untouched.
        self.company1.refresh_from_db()
        self.assertEqual(self.company1.name, "Alpha Design Studio")

    def test_soft_deleted_company_returns_404(self):
        """
        BE-018: a soft-deleted company 404s for GET and PATCH regardless of
        who's asking — including a Platform Admin — since SoftDeleteManager
        excludes it from the default `objects` queryset CompanyService reads
        from. Isolated from the delete-endpoint flow so it tests the
        soft-deleted *state* directly, not just the immediate post-delete
        response.
        """
        self.company1.delete()  # soft delete via SoftDeleteModel

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.superadmin_token}")

        get_response = self.client.get(f"/companies/{self.company1.id}")
        self.assertEqual(get_response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(get_response.json()["error"]["code"], "NOT_FOUND")

        patch_response = self.client.patch(
            f"/companies/{self.company1.id}",
            {"name": "Should Not Apply"},
            format="json",
        )
        self.assertEqual(patch_response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(patch_response.json()["error"]["code"], "NOT_FOUND")

    def test_update_company_as_member(self):
        """
        Verify company member can update their own company's details.
        """
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.member_token}")
        payload = {
            "name": "Alpha Design Studio Updated",
            "gstNumber": "27BBBBB2222B2Z2",
            "status": "suspended",  # Attempt to change status (should be ignored for non-admin)
        }
        response = self.client.patch(f"/companies/{self.company1.id}", payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data["data"]["name"], "Alpha Design Studio Updated")
        self.assertEqual(data["data"]["gstNumber"], "27BBBBB2222B2Z2")
        # Status remains active because non-admins cannot change tenant status
        self.assertEqual(data["data"]["status"], "active")

    def test_update_company_as_platform_admin_can_change_status(self):
        """
        Verify Platform Admin can update company status.
        """
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.superadmin_token}")
        payload = {"status": "suspended"}
        response = self.client.patch(f"/companies/{self.company1.id}", payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["data"]["status"], "suspended")

    def test_delete_company_as_platform_admin_soft_deletes(self):
        """
        Verify Platform Admin can soft-delete a company (200 OK).
        """
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.superadmin_token}")
        response = self.client.delete(f"/companies/{self.company2.id}")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.json()["success"])

        # Subsequent retrieval returns 404
        get_resp = self.client.get(f"/companies/{self.company2.id}")
        self.assertEqual(get_resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_delete_company_as_regular_user_fails_403(self):
        """
        Verify regular user cannot delete a company (403 Permission Error).
        """
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.member_token}")
        response = self.client.delete(f"/companies/{self.company1.id}")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.json()["error"]["code"], "PERMISSION_ERROR")

    def test_nonexistent_company_returns_404(self):
        """
        Verify querying a non-existent company UUID returns 404 Not Found.
        """
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.superadmin_token}")
        random_uuid = uuid.uuid4()
        response = self.client.get(f"/companies/{random_uuid}")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.json()["error"]["code"], "NOT_FOUND")
