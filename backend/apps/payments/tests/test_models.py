import uuid
from decimal import Decimal

from django.test import TestCase

from apps.clients.models import Client
from apps.company.models import Company, CompanyStatus
from apps.invoices.models import Invoice
from apps.payments.models import Payment
from apps.projects.models import Project


class PaymentModelTestCase(TestCase):
    """
    Unit test suite for Payment domain model (BE-043).
    """

    def setUp(self):
        self.company = Company.objects.create(name="Test Company", status=CompanyStatus.ACTIVE)
        self.client_obj = Client.objects.create(company=self.company, name="Jane Doe")
        self.project = Project.objects.create(
            company=self.company, client=self.client_obj, name="Kitchen Remodel"
        )
        self.invoice = Invoice.objects.create(
            company=self.company, project=self.project, client=self.client_obj,
            invoice_number="INV-000001", total=Decimal("500.00"),
        )

    def _create_payment(self, **overrides):
        fields = dict(
            company=self.company,
            invoice=self.invoice,
            client=self.client_obj,
            project=self.project,
            payment_date="2026-09-01",
            amount=Decimal("100.00"),
        )
        fields.update(overrides)
        return Payment.objects.create(**fields)

    def test_payment_creation_defaults(self):
        payment = self._create_payment()
        self.assertIsInstance(payment.id, uuid.UUID)
        self.assertEqual(payment.amount, Decimal("100.00"))
        self.assertEqual(payment.method, "")
        self.assertFalse(payment.is_deleted)

    def test_payment_str_representation(self):
        payment = self._create_payment()
        self.assertEqual(str(payment), f"100.00 for INV-000001")

    def test_payment_requires_invoice(self):
        with self.assertRaises(Exception):
            Payment.objects.create(
                company=self.company, client=self.client_obj, project=self.project,
                payment_date="2026-09-01", amount=Decimal("100.00"),
            )

    def test_payment_invoice_cascade_delete(self):
        payment = self._create_payment()
        payment_id = payment.id
        self.invoice.delete(hard=True)
        self.assertFalse(Payment.all_objects.filter(id=payment_id).exists())

    def test_payment_soft_delete_lifecycle(self):
        payment = self._create_payment()
        payment_id = payment.id

        payment.delete()
        self.assertTrue(payment.is_deleted)
        self.assertFalse(Payment.objects.filter(id=payment_id).exists())
        self.assertTrue(Payment.all_objects.filter(id=payment_id).exists())

        payment.restore()
        self.assertTrue(Payment.objects.filter(id=payment_id).exists())

    def test_reverse_accessor_from_invoice(self):
        self._create_payment()
        self.assertEqual(self.invoice.payments.count(), 1)
