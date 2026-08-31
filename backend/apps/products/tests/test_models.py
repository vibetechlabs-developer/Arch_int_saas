import uuid
from django.test import TestCase

from apps.company.models import Company, CompanyStatus
from apps.products.models import ProductCategory, ProductSubcategory


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


class ProductSubcategoryModelTestCase(TestCase):
    """
    Unit test suite for ProductSubcategory domain model (BE-032).
    """

    def setUp(self):
        self.company = Company.objects.create(name="Test Company", status=CompanyStatus.ACTIVE)
        self.other_company = Company.objects.create(name="Other Company", status=CompanyStatus.ACTIVE)
        self.category = ProductCategory.objects.create(company=self.company, name="Flooring")

    def test_subcategory_creation_with_required_fields(self):
        subcategory = ProductSubcategory.objects.create(
            company=self.company, category=self.category, name="Tiles"
        )
        self.assertIsInstance(subcategory.id, uuid.UUID)
        self.assertEqual(subcategory.name, "Tiles")
        self.assertEqual(subcategory.company, self.company)
        self.assertEqual(subcategory.category, self.category)
        self.assertFalse(subcategory.is_deleted)

    def test_subcategory_str_representation(self):
        subcategory = ProductSubcategory.objects.create(
            company=self.company, category=self.category, name="Tiles"
        )
        self.assertEqual(str(subcategory), f"Tiles ({self.category.name})")

    def test_subcategory_no_uniqueness_constraint_on_name(self):
        sub1 = ProductSubcategory.objects.create(
            company=self.company, category=self.category, name="Tiles"
        )
        sub2 = ProductSubcategory.objects.create(
            company=self.company, category=self.category, name="Tiles"
        )
        self.assertNotEqual(sub1.id, sub2.id)

    def test_subcategory_tenant_isolation_via_company_fk(self):
        other_category = ProductCategory.objects.create(
            company=self.other_company, name="Lighting"
        )
        ProductSubcategory.objects.create(company=self.company, category=self.category, name="Tiles")
        ProductSubcategory.objects.create(
            company=self.other_company, category=other_category, name="Bulbs"
        )

        company_subcats = ProductSubcategory.objects.filter(company=self.company)
        self.assertEqual(company_subcats.count(), 1)
        self.assertEqual(company_subcats.first().name, "Tiles")

    def test_subcategory_soft_delete_lifecycle(self):
        subcategory = ProductSubcategory.objects.create(
            company=self.company, category=self.category, name="Tiles"
        )
        subcategory_id = subcategory.id

        subcategory.delete()
        self.assertTrue(subcategory.is_deleted)

        self.assertFalse(ProductSubcategory.objects.filter(id=subcategory_id).exists())
        self.assertTrue(ProductSubcategory.all_objects.filter(id=subcategory_id).exists())

        subcategory.restore()
        self.assertTrue(ProductSubcategory.objects.filter(id=subcategory_id).exists())

    def test_subcategory_category_cascade_delete(self):
        """
        category uses CASCADE (not PROTECT, unlike Project.client) — hard
        deleting the Category removes its Subcategories.
        """
        subcategory = ProductSubcategory.objects.create(
            company=self.company, category=self.category, name="Tiles"
        )
        subcategory_id = subcategory.id
        self.category.delete(hard=True)
        self.assertFalse(ProductSubcategory.all_objects.filter(id=subcategory_id).exists())

    def test_subcategory_company_cascade_delete(self):
        subcategory = ProductSubcategory.objects.create(
            company=self.company, category=self.category, name="Tiles"
        )
        subcategory_id = subcategory.id
        self.company.delete(hard=True)
        self.assertFalse(ProductSubcategory.all_objects.filter(id=subcategory_id).exists())

    def test_subcategory_requires_category(self):
        with self.assertRaises(Exception):
            ProductSubcategory.objects.create(company=self.company, name="Orphan Subcategory")

    def test_subcategory_reverse_accessor_from_category(self):
        ProductSubcategory.objects.create(company=self.company, category=self.category, name="Tiles")
        self.assertEqual(self.category.subcategories.count(), 1)

    def test_category_soft_delete_leaves_subcategory_fk_untouched(self):
        """
        SoftDeleteModel.delete() never calls super().delete() (BE-024's
        finding), so soft-deleting the parent Category never triggers the
        `category` FK's on_delete behavior — the Subcategory row and its
        FK stay intact and resolvable.
        """
        subcategory = ProductSubcategory.objects.create(
            company=self.company, category=self.category, name="Tiles"
        )
        self.category.delete()

        subcategory.refresh_from_db()
        self.assertEqual(subcategory.category_id, self.category.id)
        self.assertFalse(subcategory.is_deleted)
