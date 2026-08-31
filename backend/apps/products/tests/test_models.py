import uuid
from django.test import TestCase

from apps.company.models import Company, CompanyStatus
from apps.products.models import ProductCategory


class ProductCategoryModelTestCase(TestCase):
    """
    Unit test suite for ProductCategory domain model (BE-031).
    """

    def setUp(self):
        self.company = Company.objects.create(name="Test Company", status=CompanyStatus.ACTIVE)
        self.other_company = Company.objects.create(name="Other Company", status=CompanyStatus.ACTIVE)

    def test_category_creation_with_required_fields(self):
        category = ProductCategory.objects.create(company=self.company, name="Flooring")
        self.assertIsInstance(category.id, uuid.UUID)
        self.assertEqual(category.name, "Flooring")
        self.assertEqual(category.company, self.company)
        self.assertIsNotNone(category.created_at)
        self.assertIsNone(category.deleted_at)
        self.assertFalse(category.is_deleted)

    def test_category_str_representation(self):
        category = ProductCategory.objects.create(company=self.company, name="Flooring")
        self.assertEqual(str(category), f"Flooring ({self.company.name})")

    def test_category_no_uniqueness_constraint_on_name(self):
        """
        Not documented anywhere — two categories with an identical name in
        the SAME company must both save successfully, matching the Client
        precedent (no invented uniqueness constraint).
        """
        cat1 = ProductCategory.objects.create(company=self.company, name="Flooring")
        cat2 = ProductCategory.objects.create(company=self.company, name="Flooring")
        self.assertNotEqual(cat1.id, cat2.id)

    def test_category_same_name_different_company_allowed(self):
        cat1 = ProductCategory.objects.create(company=self.company, name="Flooring")
        cat2 = ProductCategory.objects.create(company=self.other_company, name="Flooring")
        self.assertEqual(cat1.name, cat2.name)
        self.assertNotEqual(cat1.company_id, cat2.company_id)

    def test_category_tenant_isolation_via_company_fk(self):
        ProductCategory.objects.create(company=self.company, name="Company A Category")
        ProductCategory.objects.create(company=self.other_company, name="Company B Category")

        company_categories = ProductCategory.objects.filter(company=self.company)
        self.assertEqual(company_categories.count(), 1)
        self.assertEqual(company_categories.first().name, "Company A Category")

    def test_category_soft_delete_lifecycle(self):
        category = ProductCategory.objects.create(company=self.company, name="Flooring")
        category_id = category.id

        category.delete()
        self.assertTrue(category.is_deleted)
        self.assertIsNotNone(category.deleted_at)

        self.assertFalse(ProductCategory.objects.filter(id=category_id).exists())
        self.assertTrue(ProductCategory.all_objects.filter(id=category_id).exists())

        category.restore()
        self.assertFalse(category.is_deleted)
        self.assertTrue(ProductCategory.objects.filter(id=category_id).exists())

    def test_category_cascade_delete_with_company(self):
        category = ProductCategory.objects.create(company=self.company, name="Flooring")
        category_id = category.id
        self.company.delete(hard=True)
        self.assertFalse(ProductCategory.all_objects.filter(id=category_id).exists())

    def test_category_requires_company(self):
        with self.assertRaises(Exception):
            ProductCategory.objects.create(name="Orphan Category")

    def test_category_company_name_composite_index_exists(self):
        index_names = {index.name for index in ProductCategory._meta.indexes}
        self.assertIn("product_cat_comp_name_idx", index_names)
