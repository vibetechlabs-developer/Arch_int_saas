import uuid
from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from apps.authentication.tokens import CompanyUserAccessToken, PlatformAdminAccessToken
from apps.company.models import Company, CompanyStatus
from apps.products.models import ProductCategory
from apps.users.models import CompanyMembership, CompanyMembershipStatus

User = get_user_model()


class ProductCategoryViewSetTestCase(TestCase):
    """
    Integration test suite for ProductCategory CRUD endpoints (BE-031).
    """

    def setUp(self):
        self.client = APIClient()

        self.superadmin = User.objects.create_superuser(
            email="superadmin@example.com", name="Super Admin", password="StrongPassword123!"
        )
        self.superadmin_token = str(PlatformAdminAccessToken.for_user(self.superadmin))

        self.member_user = User.objects.create_user(
            email="alice@company1.com", name="Alice Member", password="StrongPassword123!"
        )
        self.member_token = str(CompanyUserAccessToken.for_user(self.member_user))

        self.non_member_user = User.objects.create_user(
            email="bob@outsider.com", name="Bob Outsider", password="StrongPassword123!"
        )
        self.non_member_token = str(CompanyUserAccessToken.for_user(self.non_member_user))

        self.revoked_user = User.objects.create_user(
            email="carol@company1.com", name="Carol Revoked", password="StrongPassword123!"
        )
        self.revoked_token = str(CompanyUserAccessToken.for_user(self.revoked_user))

        self.company1 = Company.objects.create(name="Studio One", status=CompanyStatus.ACTIVE)
        self.company2 = Company.objects.create(name="Studio Two", status=CompanyStatus.ACTIVE)

        CompanyMembership.objects.create(
            company=self.company1, user=self.member_user, status=CompanyMembershipStatus.ACTIVE
        )
        CompanyMembership.objects.create(
            company=self.company1, user=self.revoked_user, status=CompanyMembershipStatus.REVOKED
        )

        self.category1 = ProductCategory.objects.create(company=self.company1, name="Flooring")
        self.category2 = ProductCategory.objects.create(company=self.company1, name="Lighting")
        self.category_c2 = ProductCategory.objects.create(company=self.company2, name="Furniture")

    # --- Authentication / Authorization ---------------------------------

    def test_unauthenticated_requests_fail_401(self):
        resp_list = self.client.get("/product-categories")
        self.assertEqual(resp_list.status_code, status.HTTP_401_UNAUTHORIZED)

        resp_create = self.client.post("/product-categories", {"name": "New Category"})
        self.assertEqual(resp_create.status_code, status.HTTP_401_UNAUTHORIZED)

        resp_detail = self.client.get(f"/product-categories/{self.category1.id}")
        self.assertEqual(resp_detail.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_user_without_active_membership_denied_access(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.non_member_token}")
        response = self.client.get("/product-categories")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_user_with_revoked_membership_denied_access(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.revoked_token}")
        response = self.client.get("/product-categories")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    # --- List / Ordering / Pagination ------------------------------------

    def test_list_categories_as_company_member(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.member_token}")
        response = self.client.get("/product-categories")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertEqual(len(data["data"]), 2)
        names = [c["name"] for c in data["data"]]
        self.assertIn("Flooring", names)
        self.assertIn("Lighting", names)
        self.assertNotIn("Furniture", names)

    def test_list_categories_as_platform_admin_sees_all_companies(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.superadmin_token}")
        response = self.client.get("/product-categories")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.json()["data"]), 3)

    def test_ordering_categories(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.member_token}")
        response = self.client.get("/product-categories?ordering=name")

        names = [c["name"] for c in response.json()["data"]]
        self.assertEqual(names, sorted(names))

    def test_invalid_ordering_query_param_returns_400(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.member_token}")
        response = self.client.get("/product-categories?ordering=not_a_real_field")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_empty_list_shape(self):
        ProductCategory.objects.filter(company=self.company1).delete()
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.member_token}")
        response = self.client.get("/product-categories")

        data = response.json()
        self.assertEqual(data["data"], [])

    def test_soft_deleted_category_excluded_from_list(self):
        self.category1.delete()
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.member_token}")
        response = self.client.get("/product-categories")

        names = [c["name"] for c in response.json()["data"]]
        self.assertNotIn("Flooring", names)

    # --- Create ------------------------------------------------------------

    def test_create_category_as_company_member(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.member_token}")
        response = self.client.post("/product-categories", {"name": "New Category"}, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        data = response.json()["data"]
        self.assertEqual(data["name"], "New Category")
        self.assertEqual(data["companyId"], str(self.company1.id))

    def test_create_category_as_platform_admin_with_explicit_company_id(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.superadmin_token}")
        payload = {"name": "Admin Created Category", "companyId": str(self.company2.id)}
        response = self.client.post("/product-categories", payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.json()["data"]["companyId"], str(self.company2.id))

    def test_create_category_platform_admin_without_company_id_returns_400(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.superadmin_token}")
        response = self.client.post("/product-categories", {"name": "No Company"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_category_company_injection_by_member_denied(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.member_token}")
        payload = {"name": "Injected Category", "companyId": str(self.company2.id)}
        response = self.client.post("/product-categories", payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertFalse(ProductCategory.objects.filter(name="Injected Category").exists())

    def test_create_category_validation_error_400(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.member_token}")
        response = self.client.post("/product-categories", {"name": "   "}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # --- Retrieve ------------------------------------------------------------

    def test_get_category_detail_success(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.member_token}")
        response = self.client.get(f"/product-categories/{self.category1.id}")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()["data"]
        self.assertEqual(data["id"], str(self.category1.id))
        self.assertEqual(data["name"], "Flooring")

    def test_cross_tenant_idor_get_category_fails(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.member_token}")
        response = self.client.get(f"/product-categories/{self.category_c2.id}")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_cross_tenant_get_category_and_nonexistent_are_indistinguishable(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.member_token}")

        real_cross_tenant_response = self.client.get(f"/product-categories/{self.category_c2.id}")
        nonexistent_response = self.client.get(f"/product-categories/{uuid.uuid4()}")

        self.assertEqual(real_cross_tenant_response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(nonexistent_response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(
            real_cross_tenant_response.json()["error"]["code"],
            nonexistent_response.json()["error"]["code"],
        )

    def test_platform_admin_can_retrieve_any_tenant_category(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.superadmin_token}")
        response = self.client.get(f"/product-categories/{self.category_c2.id}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    # --- Update ------------------------------------------------------------

    def test_update_category_success(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.member_token}")
        response = self.client.patch(
            f"/product-categories/{self.category1.id}", {"name": "Renamed"}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["data"]["name"], "Renamed")

    def test_put_behaves_like_partial_update(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.member_token}")
        response = self.client.put(
            f"/product-categories/{self.category1.id}", {"name": "PUT Renamed"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["data"]["name"], "PUT Renamed")

    def test_cross_tenant_idor_patch_category_fails(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.member_token}")
        response = self.client.patch(
            f"/product-categories/{self.category_c2.id}", {"name": "Hacked"}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.category_c2.refresh_from_db()
        self.assertEqual(self.category_c2.name, "Furniture")

    def test_platform_admin_can_update_any_tenant_category(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.superadmin_token}")
        response = self.client.patch(
            f"/product-categories/{self.category_c2.id}", {"name": "Admin Edited"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    # --- Delete ------------------------------------------------------------

    def test_delete_category_soft_deletes(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.member_token}")
        response = self.client.delete(f"/product-categories/{self.category1.id}")

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        get_resp = self.client.get(f"/product-categories/{self.category1.id}")
        self.assertEqual(get_resp.status_code, status.HTTP_404_NOT_FOUND)

        self.category1.refresh_from_db()
        self.assertTrue(self.category1.is_deleted)

    def test_cross_tenant_idor_delete_category_fails(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.member_token}")
        response = self.client.delete(f"/product-categories/{self.category_c2.id}")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.category_c2.refresh_from_db()
        self.assertFalse(self.category_c2.is_deleted)

    def test_platform_admin_can_delete_any_tenant_category(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.superadmin_token}")
        response = self.client.delete(f"/product-categories/{self.category_c2.id}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
