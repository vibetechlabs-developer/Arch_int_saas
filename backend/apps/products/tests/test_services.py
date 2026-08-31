import uuid
from django.test import TestCase
from rest_framework import exceptions as drf_exceptions

from apps.audit.models import AuditLog
from apps.common.exceptions import ConflictError
from apps.company.models import Company, CompanyStatus
from apps.products.models import ProductCategory, ProductSubcategory
from apps.products.services import ProductCategoryService, ProductSubcategoryService


class ProductCategoryServiceTestCase(TestCase):
    """
    Unit test suite for ProductCategoryService business logic (BE-031).
    """

    def setUp(self):
        self.company1 = Company.objects.create(name="Alpha Corp", status=CompanyStatus.ACTIVE)
        self.company2 = Company.objects.create(name="Beta Corp", status=CompanyStatus.ACTIVE)

        self.category1 = ProductCategoryService.create_category(
            company_id=self.company1.id, name="Flooring"
        )
        self.category2 = ProductCategoryService.create_category(
            company_id=self.company1.id, name="Lighting"
        )
        self.category3 = ProductCategoryService.create_category(
            company_id=self.company2.id, name="Furniture"
        )

    def test_create_category_success(self):
        category = ProductCategoryService.create_category(
            company_id=self.company1.id, name="New Category"
        )
        self.assertEqual(category.name, "New Category")
        self.assertEqual(category.company_id, self.company1.id)

    def test_create_category_nonexistent_company_raises_not_found(self):
        with self.assertRaises(drf_exceptions.NotFound):
            ProductCategoryService.create_category(company_id=uuid.uuid4(), name="Orphan")

    def test_create_category_duplicate_name_same_company_allowed(self):
        category = ProductCategoryService.create_category(
            company_id=self.company1.id, name="Flooring"
        )
        self.assertNotEqual(category.id, self.category1.id)

    def test_get_category_by_id_success(self):
        category = ProductCategoryService.get_category_by_id(self.category1.id)
        self.assertEqual(category.id, self.category1.id)

    def test_get_category_by_id_cross_tenant_raises_not_found(self):
        with self.assertRaises(drf_exceptions.NotFound):
            ProductCategoryService.get_category_by_id(
                self.category1.id, company_id=self.company2.id
            )

    def test_list_categories_filtering_by_company(self):
        categories = ProductCategoryService.list_categories(company_id=self.company1.id)
        self.assertEqual(categories.count(), 2)

    def test_list_categories_for_viewer_non_admin_uses_resolved_company(self):
        queryset = ProductCategoryService.list_categories_for_viewer(
            is_platform_admin=False,
            resolved_company_id=self.company1.id,
            admin_company_id_param=None,
        )
        self.assertEqual(queryset.count(), 2)

    def test_list_categories_for_viewer_platform_admin_sees_all(self):
        queryset = ProductCategoryService.list_categories_for_viewer(
            is_platform_admin=True,
            resolved_company_id=None,
            admin_company_id_param=None,
        )
        self.assertEqual(queryset.count(), 3)

    def test_resolve_create_target_company_id_non_admin_mismatch_denied(self):
        with self.assertRaises(drf_exceptions.PermissionDenied):
            ProductCategoryService.resolve_create_target_company_id(
                is_platform_admin=False,
                resolved_company_id=self.company1.id,
                supplied_company_id=self.company2.id,
            )

    def test_resolve_create_target_company_id_admin_requires_company_id(self):
        with self.assertRaises(drf_exceptions.ValidationError):
            ProductCategoryService.resolve_create_target_company_id(
                is_platform_admin=True,
                resolved_company_id=None,
                supplied_company_id=None,
            )

    def test_update_category_success(self):
        updated = ProductCategoryService.update_category(
            category_id=self.category1.id,
            validated_data={"name": "Renamed Category"},
        )
        self.assertEqual(updated.name, "Renamed Category")

    def test_update_category_cross_tenant_raises_not_found(self):
        with self.assertRaises(drf_exceptions.NotFound):
            ProductCategoryService.update_category(
                category_id=self.category1.id,
                validated_data={"name": "Hacked"},
                company_id=self.company2.id,
            )

    def test_update_category_blank_name_rejected(self):
        with self.assertRaises(ValueError):
            ProductCategoryService.update_category(
                category_id=self.category1.id,
                validated_data={"name": "   "},
            )

    def test_soft_delete_category(self):
        category_id = self.category1.id
        ProductCategoryService.soft_delete_category(category_id)

        with self.assertRaises(drf_exceptions.NotFound):
            ProductCategoryService.get_category_by_id(category_id)

        self.assertTrue(ProductCategory.all_objects.filter(id=category_id).exists())

    def test_create_category_writes_audit_log_entry(self):
        category = ProductCategoryService.create_category(
            company_id=self.company1.id, name="Audited Category"
        )
        entry = AuditLog.objects.get(
            entity_type="product_category", entity_id=category.id, action="create"
        )
        self.assertEqual(entry.company_id, self.company1.id)
        self.assertIsNone(entry.before_state)
        self.assertEqual(entry.after_state["name"], "Audited Category")

    def test_update_category_writes_audit_log_entry_with_before_and_after(self):
        ProductCategoryService.update_category(
            category_id=self.category1.id, validated_data={"name": "Renamed"}
        )
        entry = AuditLog.objects.filter(
            entity_type="product_category", entity_id=self.category1.id, action="update"
        ).latest("created_at")
        self.assertEqual(entry.before_state["name"], "Flooring")
        self.assertEqual(entry.after_state["name"], "Renamed")

    def test_soft_delete_category_writes_audit_log_entry(self):
        category_id = self.category1.id
        ProductCategoryService.soft_delete_category(category_id)

        entry = AuditLog.objects.get(
            entity_type="product_category", entity_id=category_id, action="delete"
        )
        self.assertEqual(entry.before_state["name"], "Flooring")
        self.assertIsNone(entry.after_state)

    def test_soft_delete_category_blocked_by_active_subcategory(self):
        """
        Resolves BE-031's documented deferral (mirrors the Client-cannot-
        delete-while-active-Projects-exist guard).
        """
        ProductSubcategoryService.create_subcategory(category=self.category1, name="Tiles")

        with self.assertRaises(ConflictError):
            ProductCategoryService.soft_delete_category(self.category1.id)

        self.assertFalse(ProductCategory.objects.get(id=self.category1.id).is_deleted)

    def test_soft_delete_category_blocked_writes_no_audit_entry(self):
        ProductSubcategoryService.create_subcategory(category=self.category1, name="Tiles")

        with self.assertRaises(ConflictError):
            ProductCategoryService.soft_delete_category(self.category1.id)

        self.assertFalse(
            AuditLog.objects.filter(
                entity_type="product_category", entity_id=self.category1.id, action="delete"
            ).exists()
        )

    def test_soft_delete_category_succeeds_with_zero_subcategories(self):
        ProductCategoryService.soft_delete_category(self.category1.id)
        self.assertTrue(ProductCategory.all_objects.get(id=self.category1.id).is_deleted)

    def test_soft_delete_category_succeeds_when_subcategory_already_deleted(self):
        subcategory = ProductSubcategoryService.create_subcategory(
            category=self.category1, name="Tiles"
        )
        ProductSubcategoryService.soft_delete_subcategory(subcategory.id)

        ProductCategoryService.soft_delete_category(self.category1.id)
        self.assertTrue(ProductCategory.all_objects.get(id=self.category1.id).is_deleted)


class ProductSubcategoryServiceTestCase(TestCase):
    """
    Unit test suite for ProductSubcategoryService business logic (BE-032).
    """

    def setUp(self):
        self.company1 = Company.objects.create(name="Alpha Corp", status=CompanyStatus.ACTIVE)
        self.company2 = Company.objects.create(name="Beta Corp", status=CompanyStatus.ACTIVE)

        self.category1 = ProductCategoryService.create_category(
            company_id=self.company1.id, name="Flooring"
        )
        self.category2 = ProductCategoryService.create_category(
            company_id=self.company2.id, name="Furniture"
        )

        self.subcategory1 = ProductSubcategoryService.create_subcategory(
            category=self.category1, name="Tiles"
        )
        self.subcategory2 = ProductSubcategoryService.create_subcategory(
            category=self.category1, name="Carpets"
        )

    def test_create_subcategory_success(self):
        subcategory = ProductSubcategoryService.create_subcategory(
            category=self.category1, name="Marble"
        )
        self.assertEqual(subcategory.name, "Marble")
        self.assertEqual(subcategory.category_id, self.category1.id)
        self.assertEqual(subcategory.company_id, self.category1.company_id)

    def test_create_subcategory_blank_name_rejected(self):
        with self.assertRaises(ValueError):
            ProductSubcategoryService.create_subcategory(category=self.category1, name="   ")

    def test_list_subcategories_for_category(self):
        subcategories = ProductSubcategoryService.list_subcategories_for_category(self.category1)
        self.assertEqual(subcategories.count(), 2)

    def test_get_subcategory_by_id_success(self):
        subcategory = ProductSubcategoryService.get_subcategory_by_id(self.subcategory1.id)
        self.assertEqual(subcategory.id, self.subcategory1.id)

    def test_get_subcategory_by_id_cross_tenant_raises_not_found(self):
        with self.assertRaises(drf_exceptions.NotFound):
            ProductSubcategoryService.get_subcategory_by_id(
                self.subcategory1.id, company_id=self.company2.id
            )

    def test_update_subcategory_success(self):
        updated = ProductSubcategoryService.update_subcategory(
            subcategory_id=self.subcategory1.id, validated_data={"name": "Renamed"}
        )
        self.assertEqual(updated.name, "Renamed")

    def test_update_subcategory_cross_tenant_raises_not_found(self):
        with self.assertRaises(drf_exceptions.NotFound):
            ProductSubcategoryService.update_subcategory(
                subcategory_id=self.subcategory1.id,
                validated_data={"name": "Hacked"},
                company_id=self.company2.id,
            )

    def test_soft_delete_subcategory(self):
        subcategory_id = self.subcategory1.id
        ProductSubcategoryService.soft_delete_subcategory(subcategory_id)

        with self.assertRaises(drf_exceptions.NotFound):
            ProductSubcategoryService.get_subcategory_by_id(subcategory_id)

        self.assertTrue(ProductSubcategory.all_objects.filter(id=subcategory_id).exists())

    def test_create_subcategory_writes_audit_log_entry(self):
        subcategory = ProductSubcategoryService.create_subcategory(
            category=self.category1, name="Audited Subcategory"
        )
        entry = AuditLog.objects.get(
            entity_type="product_subcategory", entity_id=subcategory.id, action="create"
        )
        self.assertEqual(entry.company_id, self.category1.company_id)
        self.assertEqual(entry.after_state["name"], "Audited Subcategory")
        self.assertEqual(entry.after_state["category_id"], str(self.category1.id))

    def test_update_subcategory_writes_audit_log_entry(self):
        ProductSubcategoryService.update_subcategory(
            subcategory_id=self.subcategory1.id, validated_data={"name": "Renamed"}
        )
        entry = AuditLog.objects.filter(
            entity_type="product_subcategory", entity_id=self.subcategory1.id, action="update"
        ).latest("created_at")
        self.assertEqual(entry.before_state["name"], "Tiles")
        self.assertEqual(entry.after_state["name"], "Renamed")

    def test_soft_delete_subcategory_writes_audit_log_entry(self):
        subcategory_id = self.subcategory1.id
        ProductSubcategoryService.soft_delete_subcategory(subcategory_id)

        entry = AuditLog.objects.get(
            entity_type="product_subcategory", entity_id=subcategory_id, action="delete"
        )
        self.assertEqual(entry.before_state["name"], "Tiles")
        self.assertIsNone(entry.after_state)
