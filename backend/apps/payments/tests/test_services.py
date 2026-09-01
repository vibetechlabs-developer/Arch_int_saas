from decimal import Decimal

from django.test import TestCase
from rest_framework import exceptions as drf_exceptions

from apps.clients.models import Client
from apps.common.exceptions import ConflictError
from apps.company.models import Company, CompanyStatus
from apps.invoices.models import InvoiceStatus
from apps.invoices.services import InvoiceService
from apps.payments.services import PaymentService
from apps.projects.models import Project


class PaymentServiceTestCase(TestCase):
    """
    Unit test suite for PaymentService (BE-043) and its effect on
    InvoiceService.recompute_status_from_payments.
    """

    def setUp(self):
        self.company = Company.objects.create(name="Studio One", status=CompanyStatus.ACTIVE)
        self.client_obj = Client.objects.create(company=self.company, name="Jane Doe")
        self.project = Project.objects.create(
            company=self.company, client=self.client_obj, name="Kitchen Remodel"
        )
        self.invoice = InvoiceService.create_invoice(
            project=self.project,
            items=[{"description": "X", "quantity": Decimal("1.00"), "rate": Decimal("500.00")}],
        )

    def _send(self):
        InvoiceService.send_invoice(self.invoice)
        self.invoice.refresh_from_db()

    def test_create_payment_against_draft_invoice_raises_conflict(self):
        with self.assertRaises(ConflictError):
            PaymentService.create_payment(self.invoice, payment_date="2026-09-01", amount=Decimal("100.00"))

    def test_create_payment_against_cancelled_invoice_raises_conflict(self):
        InvoiceService.cancel_invoice(self.invoice)
        self.invoice.refresh_from_db()
        with self.assertRaises(ConflictError):
            PaymentService.create_payment(self.invoice, payment_date="2026-09-01", amount=Decimal("100.00"))

    def test_partial_payment_sets_invoice_partially_paid(self):
        self._send()
        PaymentService.create_payment(self.invoice, payment_date="2026-09-01", amount=Decimal("200.00"))
        self.invoice.refresh_from_db()
        self.assertEqual(self.invoice.status, InvoiceStatus.PARTIALLY_PAID)

    def test_full_payment_sets_invoice_paid(self):
        self._send()
        PaymentService.create_payment(self.invoice, payment_date="2026-09-01", amount=Decimal("500.00"))
        self.invoice.refresh_from_db()
        self.assertEqual(self.invoice.status, InvoiceStatus.PAID)

    def test_multiple_partial_payments_accumulate_to_paid(self):
        self._send()
        PaymentService.create_payment(self.invoice, payment_date="2026-09-01", amount=Decimal("300.00"))
        self.invoice.refresh_from_db()
        PaymentService.create_payment(self.invoice, payment_date="2026-09-02", amount=Decimal("200.00"))
        self.invoice.refresh_from_db()
        self.assertEqual(self.invoice.status, InvoiceStatus.PAID)

    def test_negative_amount_raises_value_error(self):
        self._send()
        with self.assertRaises(ValueError):
            PaymentService.create_payment(self.invoice, payment_date="2026-09-01", amount=Decimal("-1.00"))

    def test_void_payment_reverts_invoice_to_sent(self):
        self._send()
        payment = PaymentService.create_payment(
            self.invoice, payment_date="2026-09-01", amount=Decimal("500.00")
        )
        self.invoice.refresh_from_db()
        self.assertEqual(self.invoice.status, InvoiceStatus.PAID)

        PaymentService.void_payment(payment)
        self.invoice.refresh_from_db()
        self.assertEqual(self.invoice.status, InvoiceStatus.SENT)

    def test_void_payment_partial_reverts_to_partially_paid(self):
        self._send()
        PaymentService.create_payment(self.invoice, payment_date="2026-09-01", amount=Decimal("300.00"))
        self.invoice.refresh_from_db()
        second = PaymentService.create_payment(
            self.invoice, payment_date="2026-09-02", amount=Decimal("200.00")
        )
        self.invoice.refresh_from_db()
        self.assertEqual(self.invoice.status, InvoiceStatus.PAID)

        PaymentService.void_payment(second)
        self.invoice.refresh_from_db()
        self.assertEqual(self.invoice.status, InvoiceStatus.PARTIALLY_PAID)

    def test_voided_payment_excluded_from_list(self):
        self._send()
        payment = PaymentService.create_payment(
            self.invoice, payment_date="2026-09-01", amount=Decimal("100.00")
        )
        PaymentService.void_payment(payment)
        self.assertEqual(PaymentService.list_payments_for_invoice(self.invoice).count(), 0)

    def test_cancelled_invoice_status_not_resurrected_by_void(self):
        self._send()
        payment = PaymentService.create_payment(
            self.invoice, payment_date="2026-09-01", amount=Decimal("300.00")
        )
        self.invoice.refresh_from_db()
        InvoiceService.cancel_invoice(self.invoice)
        self.invoice.refresh_from_db()

        PaymentService.void_payment(payment)
        self.invoice.refresh_from_db()
        self.assertEqual(self.invoice.status, InvoiceStatus.CANCELLED)

    def test_get_payment_by_id_cross_tenant_raises_not_found(self):
        self._send()
        payment = PaymentService.create_payment(
            self.invoice, payment_date="2026-09-01", amount=Decimal("100.00")
        )
        other_company = Company.objects.create(name="Studio Two", status=CompanyStatus.ACTIVE)
        with self.assertRaises(drf_exceptions.NotFound):
            PaymentService.get_payment_by_id(payment.id, company_id=other_company.id)
