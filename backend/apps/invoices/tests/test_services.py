import datetime
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone
from rest_framework import exceptions as drf_exceptions

from apps.clients.models import Client
from apps.common.exceptions import ConflictError
from apps.company.models import Company, CompanyStatus
from apps.invoices.models import InvoiceStatus
from apps.invoices.services import InvoiceService
from apps.projects.models import Project
from apps.quotations.services import QuotationService


class InvoiceServiceCreateFromQuotationTestCase(TestCase):
    """
    Unit test suite for InvoiceService.create_invoice's "from quotation"
    path (BE-042).
    """

    def setUp(self):
        self.company = Company.objects.create(name="Studio One", status=CompanyStatus.ACTIVE)
        self.client_obj = Client.objects.create(company=self.company, name="Jane Doe")
        self.project = Project.objects.create(
            company=self.company, client=self.client_obj, name="Kitchen Remodel"
        )
        self.quotation = QuotationService.create_quotation(
            project=self.project,
            items=[{"description": "Tiling", "quantity": Decimal("10.00"), "rate": Decimal("50.00")}],
            discount=Decimal("10.00"),
            tax=Decimal("18.00"),
        )

    def _approve(self):
        QuotationService.send_quotation(self.quotation)
        self.quotation.refresh_from_db()
        QuotationService.approve_quotation(self.quotation)
        self.quotation.refresh_from_db()

    def test_create_from_approved_quotation_copies_items_and_totals(self):
        self._approve()

        invoice = InvoiceService.create_invoice(project=self.project, quotation_id=self.quotation.id)

        self.assertEqual(invoice.quotation_id, self.quotation.id)
        self.assertEqual(invoice.client_id, self.client_obj.id)
        self.assertEqual(invoice.status, InvoiceStatus.DRAFT)
        self.assertEqual(invoice.invoice_number, "INV-000001")
        self.assertEqual(invoice.subtotal, self.quotation.subtotal)
        self.assertEqual(invoice.discount, self.quotation.discount)
        self.assertEqual(invoice.tax, self.quotation.tax)
        self.assertEqual(invoice.total, self.quotation.total)

        items = list(invoice.items.all())
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].description, "Tiling")

    def test_create_from_non_approved_quotation_raises_validation_error(self):
        with self.assertRaises(drf_exceptions.ValidationError):
            InvoiceService.create_invoice(project=self.project, quotation_id=self.quotation.id)

    def test_create_with_both_quotation_and_items_raises_validation_error(self):
        self._approve()
        with self.assertRaises(drf_exceptions.ValidationError):
            InvoiceService.create_invoice(
                project=self.project,
                quotation_id=self.quotation.id,
                items=[{"description": "X", "quantity": Decimal("1.00"), "rate": Decimal("1.00")}],
            )

    def test_create_with_neither_quotation_nor_items_raises_validation_error(self):
        with self.assertRaises(drf_exceptions.ValidationError):
            InvoiceService.create_invoice(project=self.project)

    def test_create_from_cross_tenant_quotation_raises_not_found(self):
        other_company = Company.objects.create(name="Studio Two", status=CompanyStatus.ACTIVE)
        other_client = Client.objects.create(company=other_company, name="Other Client")
        other_project = Project.objects.create(
            company=other_company, client=other_client, name="Other Project"
        )
        with self.assertRaises(drf_exceptions.NotFound):
            InvoiceService.create_invoice(project=other_project, quotation_id=self.quotation.id)


class InvoiceServiceCreateAdHocTestCase(TestCase):
    """
    Unit test suite for InvoiceService.create_invoice's ad hoc path
    (BE-042).
    """

    def setUp(self):
        self.company = Company.objects.create(name="Studio One", status=CompanyStatus.ACTIVE)
        self.client_obj = Client.objects.create(company=self.company, name="Jane Doe")
        self.project = Project.objects.create(
            company=self.company, client=self.client_obj, name="Kitchen Remodel"
        )

    def test_create_ad_hoc_invoice(self):
        invoice = InvoiceService.create_invoice(
            project=self.project,
            items=[{"description": "Custom work", "quantity": Decimal("2.00"), "rate": Decimal("100.00")}],
            discount=Decimal("20.00"),
            tax=Decimal("10.00"),
        )

        self.assertIsNone(invoice.quotation_id)
        self.assertEqual(invoice.subtotal, Decimal("200.00"))
        self.assertEqual(invoice.total, Decimal("190.00"))
        self.assertEqual(invoice.items.count(), 1)

    def test_create_ad_hoc_missing_description_raises(self):
        with self.assertRaises(drf_exceptions.ValidationError):
            InvoiceService.create_invoice(
                project=self.project,
                items=[{"quantity": Decimal("1.00"), "rate": Decimal("1.00")}],
            )

    def test_invoice_number_sequential_per_company(self):
        first = InvoiceService.create_invoice(
            project=self.project,
            items=[{"description": "A", "quantity": Decimal("1.00"), "rate": Decimal("1.00")}],
        )
        second = InvoiceService.create_invoice(
            project=self.project,
            items=[{"description": "B", "quantity": Decimal("1.00"), "rate": Decimal("1.00")}],
        )
        self.assertEqual(first.invoice_number, "INV-000001")
        self.assertEqual(second.invoice_number, "INV-000002")


class InvoiceServiceUpdateTestCase(TestCase):
    """
    Unit test suite for InvoiceService.update_invoice (BE-042).
    """

    def setUp(self):
        self.company = Company.objects.create(name="Studio One", status=CompanyStatus.ACTIVE)
        self.client_obj = Client.objects.create(company=self.company, name="Jane Doe")
        self.project = Project.objects.create(
            company=self.company, client=self.client_obj, name="Kitchen Remodel"
        )
        self.invoice = InvoiceService.create_invoice(
            project=self.project,
            items=[{"description": "Original", "quantity": Decimal("1.00"), "rate": Decimal("100.00")}],
        )

    def test_update_draft_invoice_replaces_items_and_recomputes_total(self):
        updated = InvoiceService.update_invoice(
            self.invoice,
            items=[{"description": "New", "quantity": Decimal("2.00"), "rate": Decimal("50.00")}],
            discount=Decimal("10.00"),
        )
        self.assertEqual(updated.subtotal, Decimal("100.00"))
        self.assertEqual(updated.discount, Decimal("10.00"))
        self.assertEqual(updated.total, Decimal("90.00"))
        self.assertEqual(updated.items.count(), 1)
        self.assertEqual(updated.items.first().description, "New")

    def test_update_without_items_keeps_existing_items(self):
        updated = InvoiceService.update_invoice(self.invoice, notes="Updated notes")
        self.assertEqual(updated.notes, "Updated notes")
        self.assertEqual(updated.items.count(), 1)
        self.assertEqual(updated.items.first().description, "Original")

    def test_update_non_draft_invoice_raises_conflict(self):
        InvoiceService.send_invoice(self.invoice)
        self.invoice.refresh_from_db()
        with self.assertRaises(ConflictError):
            InvoiceService.update_invoice(self.invoice, notes="Too late")


class InvoiceServiceStatusTransitionsTestCase(TestCase):
    """
    Unit test suite for InvoiceService.send_invoice/cancel_invoice and
    compute_effective_status (BE-042).
    """

    def setUp(self):
        self.company = Company.objects.create(name="Studio One", status=CompanyStatus.ACTIVE)
        self.client_obj = Client.objects.create(company=self.company, name="Jane Doe")
        self.project = Project.objects.create(
            company=self.company, client=self.client_obj, name="Kitchen Remodel"
        )
        self.invoice = InvoiceService.create_invoice(
            project=self.project,
            items=[{"description": "X", "quantity": Decimal("1.00"), "rate": Decimal("100.00")}],
        )

    def test_send_transitions_draft_to_sent(self):
        updated = InvoiceService.send_invoice(self.invoice)
        self.assertEqual(updated.status, InvoiceStatus.SENT)

    def test_send_twice_raises_conflict(self):
        InvoiceService.send_invoice(self.invoice)
        self.invoice.refresh_from_db()
        with self.assertRaises(ConflictError):
            InvoiceService.send_invoice(self.invoice)

    def test_cancel_from_draft_succeeds(self):
        updated = InvoiceService.cancel_invoice(self.invoice)
        self.assertEqual(updated.status, InvoiceStatus.CANCELLED)

    def test_cancel_twice_raises_conflict(self):
        InvoiceService.cancel_invoice(self.invoice)
        self.invoice.refresh_from_db()
        with self.assertRaises(ConflictError):
            InvoiceService.cancel_invoice(self.invoice)

    def test_effective_status_is_draft_when_not_due(self):
        self.assertEqual(InvoiceService.compute_effective_status(self.invoice), InvoiceStatus.DRAFT)

    def test_effective_status_overdue_when_sent_and_past_due_date(self):
        InvoiceService.send_invoice(self.invoice)
        self.invoice.refresh_from_db()
        self.invoice.due_date = timezone.localdate() - datetime.timedelta(days=1)
        self.invoice.save(update_fields=["due_date"])

        self.assertEqual(InvoiceService.compute_effective_status(self.invoice), InvoiceStatus.OVERDUE)
        # The persisted column itself is unaffected.
        self.assertEqual(self.invoice.status, InvoiceStatus.SENT)

    def test_effective_status_not_overdue_when_due_date_in_future(self):
        InvoiceService.send_invoice(self.invoice)
        self.invoice.refresh_from_db()
        self.invoice.due_date = timezone.localdate() + datetime.timedelta(days=5)
        self.invoice.save(update_fields=["due_date"])

        self.assertEqual(InvoiceService.compute_effective_status(self.invoice), InvoiceStatus.SENT)

    def test_effective_status_cancelled_is_never_overdue(self):
        InvoiceService.send_invoice(self.invoice)
        self.invoice.refresh_from_db()
        self.invoice.due_date = timezone.localdate() - datetime.timedelta(days=1)
        self.invoice.status = InvoiceStatus.CANCELLED
        self.invoice.save(update_fields=["due_date", "status"])

        self.assertEqual(InvoiceService.compute_effective_status(self.invoice), InvoiceStatus.CANCELLED)


class InvoiceServiceGetByIdTestCase(TestCase):
    """
    Unit test suite for InvoiceService.get_invoice_by_id (BE-042).
    """

    def setUp(self):
        self.company = Company.objects.create(name="Studio One", status=CompanyStatus.ACTIVE)
        self.client_obj = Client.objects.create(company=self.company, name="Jane Doe")
        self.project = Project.objects.create(
            company=self.company, client=self.client_obj, name="Kitchen Remodel"
        )
        self.invoice = InvoiceService.create_invoice(
            project=self.project,
            items=[{"description": "X", "quantity": Decimal("1.00"), "rate": Decimal("100.00")}],
        )

    def test_get_by_id_success(self):
        found = InvoiceService.get_invoice_by_id(self.invoice.id)
        self.assertEqual(found.id, self.invoice.id)

    def test_get_by_id_cross_tenant_raises_not_found(self):
        other_company = Company.objects.create(name="Studio Two", status=CompanyStatus.ACTIVE)
        with self.assertRaises(drf_exceptions.NotFound):
            InvoiceService.get_invoice_by_id(self.invoice.id, company_id=other_company.id)
