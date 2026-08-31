from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from apps.authentication.tokens import CompanyUserAccessToken
from apps.company.models import Company, CompanyStatus
from apps.products.models import Product, ProductCategory, ProductStatus, ProductSubcategory
from apps.products.services import ProductService
from apps.users.models import CompanyMembership, CompanyMembershipStatus

User = get_user_model()


class ProductListFilterServiceTestCase(TestCase):
    """
    Unit tests for ProductService.list_products filtering (BE-034).
    """

    def setUp(self):
        self.company = Company.objects.create(name="Alpha Corp", status=CompanyStatus.ACTIVE)

        self.category_a = ProductCategory.objects.create(company=self.company, name="Flooring")
        self.category_b = ProductCategory.objects.create(company=self.company, name="Lighting")

        self.subcategory_a = ProductSubcategory.objects.create(
            company=self.company, category=self.category_a, name="Tiles"
        )
        self.subcategory_b = ProductSubcategory.objects.create(
            company=self.company, category=self.category_b, name="Bulbs"
        )

        self.product_active_a = Product.objects.create(
            company=self.company,
            subcategory=self.subcategory_a,
            name="Ceramic Tile",
            status=ProductStatus.ACTIVE,
        )
        self.product_inactive_a = Product.objects.create(
            company=self.company,
            subcategory=self.subcategory_a,
            name="Discontinued Tile",
            status=ProductStatus.INACTIVE,
        )
        self.product_active_b = Product.objects.create(
            company=self.company,
            subcategory=self.subcategory_b,
            name="LED Bulb",
            status=ProductStatus.ACTIVE,
        )

    def test_filter_by_category(self):
        result = ProductService.list_products(company_id=self.company.id, category_id=self.category_a.id)
        self.assertEqual(
            {p.id for p in result},
            {self.product_active_a.id, self.product_inactive_a.id},
        )

    def test_filter_by_subcategory(self):
        result = ProductService.list_products(
            company_id=self.company.id, subcategory_id=self.subcategory_b.id
        )
        self.assertEqual({p.id for p in result}, {self.product_active_b.id})

    def test_filter_by_status(self):
        result = ProductService.list_products(company_id=self.company.id, status=ProductStatus.INACTIVE)
        self.assertEqual({p.id for p in result}, {self.product_inactive_a.id})

    def test_combined_filters_narrow_results(self):
        result = ProductService.list_products(
            company_id=self.company.id,
            category_id=self.category_a.id,
            status=ProductStatus.ACTIVE,
        )
        self.assertEqual({p.id for p in result}, {self.product_active_a.id})

    def test_no_filters_returns_all(self):
        result = ProductService.list_products(company_id=self.company.id)
        self.assertEqual(result.count(), 3)


class ProductListFilterEndpointTestCase(TestCase):
    """
    Integration tests for GET /products filter query params (BE-034).
    """

    def setUp(self):
        self.client = APIClient()

        self.member_user = User.objects.create_user(
            email="alice@company1.com", name="Alice Member", password="StrongPassword123!"
        )
        self.member_token = str(CompanyUserAccessToken.for_user(self.member_user))

        self.company1 = Company.objects.create(name="Studio One", status=CompanyStatus.ACTIVE)
        CompanyMembership.objects.create(
            company=self.company1, user=self.member_user, status=CompanyMembershipStatus.ACTIVE
        )

        self.category = ProductCategory.objects.create(company=self.company1, name="Flooring")
        self.subcategory = ProductSubcategory.objects.create(
            company=self.company1, category=self.category, name="Tiles"
        )

        self.product_active = Product.objects.create(
            company=self.company1,
            subcategory=self.subcategory,
            name="Ceramic Tile",
            status=ProductStatus.ACTIVE,
        )
        self.product_inactive = Product.objects.create(
            company=self.company1,
            subcategory=self.subcategory,
            name="Discontinued Tile",
            status=ProductStatus.INACTIVE,
        )

    def test_filter_by_status_query_param(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.member_token}")
        response = self.client.get("/products", {"status": "inactive"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()["data"]
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["name"], "Discontinued Tile")

    def test_filter_by_category_query_param(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.member_token}")
        response = self.client.get("/products", {"category": str(self.category.id)})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.json()["data"]), 2)

    def test_filter_by_subcategory_query_param(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.member_token}")
        response = self.client.get("/products", {"subcategory": str(self.subcategory.id)})
        self.assertEqual(len(response.json()["data"]), 2)

    def test_invalid_status_value_returns_400(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.member_token}")
        response = self.client.get("/products", {"status": "not-a-real-status"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_no_filters_returns_all(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.member_token}")
        response = self.client.get("/products")
        self.assertEqual(len(response.json()["data"]), 2)
