import uuid
from decimal import Decimal

from django.test import TestCase

from apps.clients.models import Client
from apps.company.models import Company, CompanyStatus
from apps.invoices.models import Invoice, InvoiceItem, InvoiceStatus
from apps.products.models import ProductUnit
from apps.projects.models import Project


class InvoiceModelTestCase(TestCase):
    """
    Unit test suite for Invoice domain model (BE-042).
    """

    def setUp(self):
        self.company = Company.objects.create(name="Test Company", status=CompanyStatus.ACTIVE)
        self.client_obj = Client.objects.create(company=self.company, name="Jane Doe")
        self.project = Project.objects.create(
            company=self.company, client=self.client_obj, name="Kitchen Remodel"
        )

    def _create_invoice(self, **overrides):
        fields = dict(
            company=self.company,
            project=self.project,
            client=self.client_obj,
            invoice_number="INV-000001",
        )
        fields.update(overrides)
        return Invoice.objects.create(**fields)

    def test_invoice_creation_defaults(self):
        invoice = self._create_invoice()
        self.assertIsInstance(invoice.id, uuid.UUID)
        self.assertEqual(invoice.status, InvoiceStatus.DRAFT)
        self.assertEqual(invoice.subtotal, 0)
        self.assertIsNone(invoice.quotation_id)
        self.assertFalse(invoice.is_deleted)

    def test_invoice_has_no_contract_column(self):
        self.assertFalse(hasattr(Invoice, "contract"))
        self.assertFalse(hasattr(Invoice, "contract_id"))

    def test_invoice_str_representation(self):
        invoice = self._create_invoice()
        self.assertEqual(str(invoice), f"INV-000001 ({self.project.name})")

    def test_invoice_requires_project(self):
        with self.assertRaises(Exception):
            Invoice.objects.create(
                company=self.company, client=self.client_obj, invoice_number="INV-000001"
            )

    def test_invoice_cascade_delete_with_project(self):
        invoice = self._create_invoice()
        invoice_id = invoice.id
        self.project.delete(hard=True)
        self.assertFalse(Invoice.all_objects.filter(id=invoice_id).exists())

    def test_invoice_soft_delete_lifecycle(self):
        invoice = self._create_invoice()
        invoice_id = invoice.id

        invoice.delete()
        self.assertTrue(invoice.is_deleted)
        self.assertFalse(Invoice.objects.filter(id=invoice_id).exists())
        self.assertTrue(Invoice.all_objects.filter(id=invoice_id).exists())

        invoice.restore()
        self.assertTrue(Invoice.objects.filter(id=invoice_id).exists())

    def test_reverse_accessor_from_project(self):
        self._create_invoice()
        self.assertEqual(self.project.invoices.count(), 1)


class InvoiceItemModelTestCase(TestCase):
    """
    Unit test suite for InvoiceItem domain model (BE-042).
    """

    def setUp(self):
        self.company = Company.objects.create(name="Test Company", status=CompanyStatus.ACTIVE)
        self.client_obj = Client.objects.create(company=self.company, name="Jane Doe")
        self.project = Project.objects.create(
            company=self.company, client=self.client_obj, name="Kitchen Remodel"
        )
        self.invoice = Invoice.objects.create(
            company=self.company, project=self.project, client=self.client_obj,
            invoice_number="INV-000001",
        )

    def test_item_creation(self):
        item = InvoiceItem.objects.create(
            invoice=self.invoice,
            description="Custom work",
            quantity=Decimal("10.00"),
            unit=ProductUnit.SQFT,
            rate=Decimal("50.00"),
            amount=Decimal("500.00"),
        )
        self.assertIsInstance(item.id, uuid.UUID)
        self.assertEqual(item.amount, Decimal("500.00"))

    def test_item_has_no_product_column(self):
        self.assertFalse(hasattr(InvoiceItem, "product"))
        self.assertFalse(hasattr(InvoiceItem, "product_id"))

    def test_item_str_representation(self):
        item = InvoiceItem.objects.create(
            invoice=self.invoice, description="Custom work", quantity=Decimal("1.00"),
            unit=ProductUnit.JOB, rate=Decimal("100.00"), amount=Decimal("100.00"),
        )
        self.assertEqual(str(item), f"Custom work ({self.invoice.id})")

    def test_item_requires_invoice(self):
        with self.assertRaises(Exception):
            InvoiceItem.objects.create(
                description="Orphan Item", quantity=Decimal("1.00"), rate=Decimal("1.00"), amount=Decimal("1.00"),
            )

    def test_item_invoice_cascade_delete(self):
        item = InvoiceItem.objects.create(
            invoice=self.invoice, description="Custom work", quantity=Decimal("1.00"),
            rate=Decimal("1.00"), amount=Decimal("1.00"),
        )
        item_id = item.id
        self.invoice.delete(hard=True)
        self.assertFalse(InvoiceItem.all_objects.filter(id=item_id).exists())

    def test_reverse_accessor_from_invoice(self):
        InvoiceItem.objects.create(
            invoice=self.invoice, description="Custom work", quantity=Decimal("1.00"),
            rate=Decimal("1.00"), amount=Decimal("1.00"),
        )
        self.assertEqual(self.invoice.items.count(), 1)
