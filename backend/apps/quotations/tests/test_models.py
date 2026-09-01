import uuid
from decimal import Decimal

from django.db import IntegrityError, transaction
from django.test import TestCase

from apps.clients.models import Client
from apps.company.models import Company, CompanyStatus
from apps.products.models import Product, ProductCategory, ProductSubcategory, ProductUnit
from apps.projects.models import Project
from apps.quotations.models import Quotation, QuotationItem, QuotationStatus


class QuotationModelTestCase(TestCase):
    """
    Unit test suite for Quotation domain model (BE-039).
    """

    def setUp(self):
        self.company = Company.objects.create(name="Test Company", status=CompanyStatus.ACTIVE)
        self.client_obj = Client.objects.create(company=self.company, name="Jane Doe")
        self.project = Project.objects.create(
            company=self.company, client=self.client_obj, name="Kitchen Remodel"
        )

    def _create_quotation(self, **overrides):
        fields = dict(
            company=self.company,
            project=self.project,
            client=self.client_obj,
            quote_number="QT-000001",
            version=1,
        )
        fields.update(overrides)
        return Quotation.objects.create(**fields)

    def test_quotation_creation_defaults(self):
        quotation = self._create_quotation()
        self.assertIsInstance(quotation.id, uuid.UUID)
        self.assertEqual(quotation.status, QuotationStatus.DRAFT)
        self.assertEqual(quotation.version, 1)
        self.assertEqual(quotation.subtotal, 0)
        self.assertEqual(quotation.payment_schedule, [])
        self.assertIsNone(quotation.boq_id)
        self.assertFalse(quotation.is_deleted)

    def test_quotation_str_representation(self):
        quotation = self._create_quotation()
        self.assertEqual(str(quotation), f"QT-000001 v1 ({self.project.name})")

    def test_quotation_requires_project(self):
        with self.assertRaises(Exception):
            Quotation.objects.create(
                company=self.company, client=self.client_obj, quote_number="QT-000001", version=1
            )

    def test_quotation_unique_company_quote_number_version(self):
        self._create_quotation()
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                self._create_quotation()

    def test_quotation_same_quote_number_different_version_allowed(self):
        self._create_quotation(version=1)
        second = self._create_quotation(version=2)
        self.assertEqual(second.version, 2)
        self.assertEqual(second.quote_number, "QT-000001")

    def test_quotation_cascade_delete_with_project(self):
        quotation = self._create_quotation()
        quotation_id = quotation.id
        self.project.delete(hard=True)
        self.assertFalse(Quotation.all_objects.filter(id=quotation_id).exists())

    def test_quotation_soft_delete_lifecycle(self):
        quotation = self._create_quotation()
        quotation_id = quotation.id

        quotation.delete()
        self.assertTrue(quotation.is_deleted)
        self.assertFalse(Quotation.objects.filter(id=quotation_id).exists())
        self.assertTrue(Quotation.all_objects.filter(id=quotation_id).exists())

        quotation.restore()
        self.assertTrue(Quotation.objects.filter(id=quotation_id).exists())

    def test_reverse_accessor_from_project(self):
        self._create_quotation()
        self.assertEqual(self.project.quotations.count(), 1)


class QuotationItemModelTestCase(TestCase):
    """
    Unit test suite for QuotationItem domain model (BE-039).
    """

    def setUp(self):
        self.company = Company.objects.create(name="Test Company", status=CompanyStatus.ACTIVE)
        self.client_obj = Client.objects.create(company=self.company, name="Jane Doe")
        self.project = Project.objects.create(
            company=self.company, client=self.client_obj, name="Kitchen Remodel"
        )
        self.quotation = Quotation.objects.create(
            company=self.company,
            project=self.project,
            client=self.client_obj,
            quote_number="QT-000001",
            version=1,
        )
        self.category = ProductCategory.objects.create(company=self.company, name="Flooring")
        self.subcategory = ProductSubcategory.objects.create(
            company=self.company, category=self.category, name="Tiles"
        )
        self.product = Product.objects.create(
            company=self.company, subcategory=self.subcategory, name="Ceramic Tile"
        )

    def test_item_creation_free_text(self):
        item = QuotationItem.objects.create(
            quotation=self.quotation,
            description="Custom work",
            quantity=Decimal("10.00"),
            unit=ProductUnit.SQFT,
            rate=Decimal("50.00"),
            amount=Decimal("500.00"),
        )
        self.assertIsInstance(item.id, uuid.UUID)
        self.assertIsNone(item.product)
        self.assertEqual(item.amount, Decimal("500.00"))

    def test_item_creation_with_product(self):
        item = QuotationItem.objects.create(
            quotation=self.quotation,
            product=self.product,
            description=self.product.name,
            quantity=Decimal("5.00"),
            unit=ProductUnit.NOS,
            rate=Decimal("100.00"),
            amount=Decimal("500.00"),
        )
        self.assertEqual(item.product, self.product)

    def test_item_str_representation(self):
        item = QuotationItem.objects.create(
            quotation=self.quotation,
            description="Custom work",
            quantity=Decimal("1.00"),
            unit=ProductUnit.JOB,
            rate=Decimal("100.00"),
            amount=Decimal("100.00"),
        )
        self.assertEqual(str(item), f"Custom work ({self.quotation.id})")

    def test_item_requires_quotation(self):
        with self.assertRaises(Exception):
            QuotationItem.objects.create(
                description="Orphan Item",
                quantity=Decimal("1.00"),
                rate=Decimal("1.00"),
                amount=Decimal("1.00"),
            )

    def test_item_quotation_cascade_delete(self):
        item = QuotationItem.objects.create(
            quotation=self.quotation,
            description="Custom work",
            quantity=Decimal("1.00"),
            rate=Decimal("1.00"),
            amount=Decimal("1.00"),
        )
        item_id = item.id
        self.quotation.delete(hard=True)
        self.assertFalse(QuotationItem.all_objects.filter(id=item_id).exists())

    def test_item_product_set_null_on_product_hard_delete(self):
        item = QuotationItem.objects.create(
            quotation=self.quotation,
            product=self.product,
            description=self.product.name,
            quantity=Decimal("1.00"),
            rate=Decimal("1.00"),
            amount=Decimal("1.00"),
        )
        self.product.delete(hard=True)

        item.refresh_from_db()
        self.assertIsNone(item.product)
        self.assertEqual(item.description, "Ceramic Tile")

    def test_reverse_accessor_from_quotation(self):
        QuotationItem.objects.create(
            quotation=self.quotation,
            description="Custom work",
            quantity=Decimal("1.00"),
            rate=Decimal("1.00"),
            amount=Decimal("1.00"),
        )
        self.assertEqual(self.quotation.items.count(), 1)
