from decimal import Decimal
from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from apps.authentication.tokens import CompanyUserAccessToken
from apps.clients.models import Client
from apps.company.models import Company, CompanyStatus
from apps.products.models import Product, ProductCategory, ProductSubcategory, ProductUnit
from apps.projects.models import Project
from apps.users.models import CompanyMembership, CompanyMembershipStatus

User = get_user_model()


class BOQEndToEndIntegrationTestCase(TestCase):
    """
    Final Sprint 4 stabilization pass (BE-038). BOQ_API.md's entire
    documented endpoint table is already fully built across BE-035
    (BOQ Module), BE-036 (BOQ Items), and BE-037 (BOQ Calculations) --
    the same situation BE-034 ("Catalog APIs") found itself in after
    BE-031-033 had already covered every documented Product Catalog
    endpoint. This task's tests exercise the full documented flow in one
    place, end to end over real HTTP calls, rather than each task's own
    tests (which necessarily only exercise their own slice in isolation).
    """

    def setUp(self):
        self.client = APIClient()

        self.member_user = User.objects.create_user(
            email="alice@company1.com", name="Alice Member", password="StrongPassword123!"
        )
        self.member_token = str(CompanyUserAccessToken.for_user(self.member_user))

        self.company = Company.objects.create(name="Studio One", status=CompanyStatus.ACTIVE)
        CompanyMembership.objects.create(
            company=self.company, user=self.member_user, status=CompanyMembershipStatus.ACTIVE
        )

        self.client_obj = Client.objects.create(company=self.company, name="Jane Doe")
        self.project = Project.objects.create(
            company=self.company, client=self.client_obj, name="Kitchen Remodel"
        )

        self.category = ProductCategory.objects.create(company=self.company, name="Flooring")
        self.subcategory = ProductSubcategory.objects.create(
            company=self.company, category=self.category, name="Tiles"
        )
        self.product = Product.objects.create(
            company=self.company,
            subcategory=self.subcategory,
            name="Ceramic Tile",
            unit=ProductUnit.SQFT,
            default_selling_rate=Decimal("120.00"),
            tax_rate=Decimal("18.00"),
        )

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.member_token}")

    def test_full_boq_flow_project_to_summary(self):
        # 1. BOQ auto-creates on first access.
        boq_resp = self.client.get(f"/projects/{self.project.id}/boq")
        self.assertEqual(boq_resp.status_code, status.HTTP_200_OK)
        self.assertEqual(boq_resp.json()["data"]["sections"], [])

        # 2. Add a section.
        section_resp = self.client.post(
            f"/projects/{self.project.id}/boq/sections", {"name": "Flooring"}, format="json"
        )
        self.assertEqual(section_resp.status_code, status.HTTP_201_CREATED)
        section_id = section_resp.json()["data"]["id"]

        # 3. Add a free-text item and a product-referenced item.
        free_text_resp = self.client.post(
            f"/projects/{self.project.id}/boq/sections/{section_id}/items",
            {
                "description": "Custom underlay",
                "quantity": "10.00",
                "unit": "sqft",
                "rate": "20.00",
                "discount": "10.00",
            },
            format="json",
        )
        self.assertEqual(free_text_resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(free_text_resp.json()["data"]["amount"], "200.00")

        product_resp = self.client.post(
            f"/projects/{self.project.id}/boq/sections/{section_id}/items",
            {"productId": str(self.product.id), "quantity": "5.00"},
            format="json",
        )
        self.assertEqual(product_resp.status_code, status.HTTP_201_CREATED)
        product_item = product_resp.json()["data"]
        self.assertEqual(product_item["description"], "Ceramic Tile")
        self.assertEqual(product_item["amount"], "600.00")

        # 4. An optional item, excluded from the default summary total.
        optional_resp = self.client.post(
            f"/projects/{self.project.id}/boq/sections/{section_id}/items",
            {
                "description": "Optional upgrade",
                "quantity": "1.00",
                "unit": "job",
                "rate": "9999.00",
                "isOptional": True,
            },
            format="json",
        )
        self.assertEqual(optional_resp.status_code, status.HTTP_201_CREATED)

        # 5. The BOQ tree reflects every item, nested under its section.
        tree_resp = self.client.get(f"/projects/{self.project.id}/boq")
        sections = tree_resp.json()["data"]["sections"]
        self.assertEqual(len(sections), 1)
        self.assertEqual(len(sections[0]["items"]), 3)

        # 6. Edit an item; amount recomputes server-side.
        item_id = free_text_resp.json()["data"]["id"]
        patch_resp = self.client.patch(
            f"/boq-items/{item_id}", {"quantity": "5.00"}, format="json"
        )
        self.assertEqual(patch_resp.status_code, status.HTTP_200_OK)
        self.assertEqual(patch_resp.json()["data"]["amount"], "100.00")

        # 7. Summary excludes the optional item and reflects the edit.
        # Item 1 (edited): base=100.00, discount=10% -> 90.00.
        # Item 2 (product): base=600.00, tax=18% -> 600.00 + 108.00 = 708.00.
        summary_resp = self.client.get(f"/projects/{self.project.id}/boq/summary")
        self.assertEqual(summary_resp.status_code, status.HTTP_200_OK)
        summary = summary_resp.json()["data"]
        self.assertEqual(summary["subtotal"], "700.00")
        self.assertEqual(summary["discount"], "10.00")
        self.assertEqual(summary["tax"], "108.00")
        self.assertEqual(summary["total"], "798.00")

        # 8. Remove the product-referenced item; summary updates accordingly.
        product_item_id = product_item["id"]
        delete_resp = self.client.delete(f"/boq-items/{product_item_id}")
        self.assertEqual(delete_resp.status_code, status.HTTP_200_OK)

        final_summary = self.client.get(f"/projects/{self.project.id}/boq/summary").json()["data"]
        self.assertEqual(final_summary["subtotal"], "100.00")
        self.assertEqual(final_summary["total"], "90.00")

    def test_section_delete_blocked_until_items_removed_then_succeeds(self):
        section_resp = self.client.post(
            f"/projects/{self.project.id}/boq/sections", {"name": "Flooring"}, format="json"
        )
        section_id = section_resp.json()["data"]["id"]

        item_resp = self.client.post(
            f"/projects/{self.project.id}/boq/sections/{section_id}/items",
            {"description": "Custom", "quantity": "1.00", "unit": "job", "rate": "10.00"},
            format="json",
        )
        item_id = item_resp.json()["data"]["id"]

        blocked_resp = self.client.delete(f"/boq-sections/{section_id}")
        self.assertEqual(blocked_resp.status_code, status.HTTP_409_CONFLICT)

        self.client.delete(f"/boq-items/{item_id}")

        allowed_resp = self.client.delete(f"/boq-sections/{section_id}")
        self.assertEqual(allowed_resp.status_code, status.HTTP_200_OK)
