from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from apps.authentication.tokens import CompanyUserAccessToken
from apps.clients.models import Client
from apps.common.test_utils import make_full_access_membership
from apps.company.models import Company, CompanyStatus
from apps.invoices.models import Invoice, InvoiceStatus
from apps.invoices.services import InvoiceService
from apps.payments.models import Payment
from apps.payments.services import PaymentService
from apps.projects.models import Project
from apps.users.models import CompanyMembershipStatus

User = get_user_model()


class InvoicePaymentAggregatesTestCase(TestCase):
    """
    BE-074: `paidAmount`/`outstandingAmount` on InvoiceSerializer are
    backend-authoritative, sourced from `PaymentRepository`-equivalent
    aggregation (via `apps.invoices.repositories.with_paid_amount`'s
    annotation), never reconstructed on the frontend.
    """

    def setUp(self):
        self.client = APIClient()

        self.member_user = User.objects.create_user(
            email="alice@company1.com", name="Alice Member", password="StrongPassword123!"
        )
        self.member_token = str(CompanyUserAccessToken.for_user(self.member_user))

        self.company1 = Company.objects.create(name="Studio One", status=CompanyStatus.ACTIVE)
        self.company2 = Company.objects.create(name="Studio Two", status=CompanyStatus.ACTIVE)

        make_full_access_membership(
            company=self.company1, user=self.member_user, status=CompanyMembershipStatus.ACTIVE
        )

        self.client1 = Client.objects.create(company=self.company1, name="Client One")
        self.client2 = Client.objects.create(company=self.company2, name="Client Two")

        self.project1 = Project.objects.create(
            company=self.company1, client=self.client1, name="Kitchen Remodel"
        )
        self.project_c2 = Project.objects.create(
            company=self.company2, client=self.client2, name="Office Fitout"
        )

        self.invoice = InvoiceService.create_invoice(
            project=self.project1,
            items=[{"description": "Full build-out", "quantity": Decimal("1.00"), "rate": Decimal("100.00")}],
        )
        InvoiceService.send_invoice(self.invoice)
        self.invoice.refresh_from_db()

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.member_token}")

    def _get_invoice(self):
        response = self.client.get(f"/invoices/{self.invoice.id}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        return response.json()["data"]

    # 1. zero payments
    def test_zero_payments(self):
        data = self._get_invoice()
        self.assertEqual(data["paidAmount"], "0.00")
        self.assertEqual(data["outstandingAmount"], "100.00")
        self.assertEqual(data["total"], "100.00")

    # 2. one payment
    def test_one_payment(self):
        self.client.post(
            f"/invoices/{self.invoice.id}/payments",
            {"paymentDate": "2026-09-01", "amount": "40.00"},
            format="json",
        )
        data = self._get_invoice()
        self.assertEqual(data["paidAmount"], "40.00")
        self.assertEqual(data["outstandingAmount"], "60.00")

    # 3/4. multiple payments / partial payment
    def test_multiple_payments_partial(self):
        self.client.post(
            f"/invoices/{self.invoice.id}/payments", {"paymentDate": "2026-09-01", "amount": "30.00"}, format="json"
        )
        self.client.post(
            f"/invoices/{self.invoice.id}/payments", {"paymentDate": "2026-09-02", "amount": "20.00"}, format="json"
        )
        data = self._get_invoice()
        self.assertEqual(data["paidAmount"], "50.00")
        self.assertEqual(data["outstandingAmount"], "50.00")
        self.assertEqual(data["status"], "partially_paid")

    # 5. fully paid invoice
    def test_fully_paid(self):
        self.client.post(
            f"/invoices/{self.invoice.id}/payments", {"paymentDate": "2026-09-01", "amount": "100.00"}, format="json"
        )
        data = self._get_invoice()
        self.assertEqual(data["paidAmount"], "100.00")
        self.assertEqual(data["outstandingAmount"], "0.00")
        self.assertEqual(data["status"], "paid")

    # 6. overpaid invoice
    def test_overpayment_not_negative(self):
        self.client.post(
            f"/invoices/{self.invoice.id}/payments", {"paymentDate": "2026-09-01", "amount": "120.00"}, format="json"
        )
        data = self._get_invoice()
        self.assertEqual(data["paidAmount"], "120.00")
        self.assertEqual(data["outstandingAmount"], "0.00")
        self.assertEqual(data["status"], "paid")

    # 7. voided payment excluded
    def test_voided_payment_excluded(self):
        create_resp = self.client.post(
            f"/invoices/{self.invoice.id}/payments", {"paymentDate": "2026-09-01", "amount": "60.00"}, format="json"
        )
        payment_id = create_resp.json()["data"]["id"]
        self.client.post(
            f"/invoices/{self.invoice.id}/payments", {"paymentDate": "2026-09-02", "amount": "10.00"}, format="json"
        )

        self.client.delete(f"/payments/{payment_id}")

        data = self._get_invoice()
        self.assertEqual(data["paidAmount"], "10.00")
        self.assertEqual(data["outstandingAmount"], "90.00")

    # 8. create payment updates aggregate
    def test_create_payment_updates_aggregate(self):
        before = self._get_invoice()
        self.assertEqual(before["paidAmount"], "0.00")

        self.client.post(
            f"/invoices/{self.invoice.id}/payments", {"paymentDate": "2026-09-01", "amount": "25.00"}, format="json"
        )

        after = self._get_invoice()
        self.assertEqual(after["paidAmount"], "25.00")

    # 9. void payment updates aggregate
    def test_void_payment_updates_aggregate(self):
        create_resp = self.client.post(
            f"/invoices/{self.invoice.id}/payments", {"paymentDate": "2026-09-01", "amount": "100.00"}, format="json"
        )
        payment_id = create_resp.json()["data"]["id"]
        self.assertEqual(self._get_invoice()["paidAmount"], "100.00")

        self.client.delete(f"/payments/{payment_id}")

        after = self._get_invoice()
        self.assertEqual(after["paidAmount"], "0.00")
        self.assertEqual(after["outstandingAmount"], "100.00")
        self.assertEqual(after["status"], "sent")

    # 10. different invoice payments never leak
    def test_different_invoice_payments_do_not_leak(self):
        other_invoice = InvoiceService.create_invoice(
            project=self.project1,
            items=[{"description": "Other", "quantity": Decimal("1.00"), "rate": Decimal("50.00")}],
        )
        InvoiceService.send_invoice(other_invoice)
        other_invoice.refresh_from_db()

        self.client.post(
            f"/invoices/{self.invoice.id}/payments", {"paymentDate": "2026-09-01", "amount": "30.00"}, format="json"
        )

        other_resp = self.client.get(f"/invoices/{other_invoice.id}")
        other_data = other_resp.json()["data"]
        self.assertEqual(other_data["paidAmount"], "0.00")
        self.assertEqual(other_data["outstandingAmount"], "50.00")

    # 11. different tenant payments never leak / tenant isolation preserved
    def test_cross_tenant_invoice_returns_404_no_leak(self):
        invoice_c2 = Invoice.objects.create(
            company=self.company2,
            project=self.project_c2,
            client=self.client2,
            invoice_number="INV-000001",
            total=Decimal("500.00"),
            status=InvoiceStatus.SENT,
        )
        Payment.objects.create(
            company=self.company2,
            invoice=invoice_c2,
            client=self.client2,
            project=self.project_c2,
            payment_date="2026-09-01",
            amount=Decimal("500.00"),
        )

        response = self.client.get(f"/invoices/{invoice_c2.id}")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    # 12. decimal precision correct
    def test_decimal_precision(self):
        self.client.post(
            f"/invoices/{self.invoice.id}/payments", {"paymentDate": "2026-09-01", "amount": "33.33"}, format="json"
        )
        data = self._get_invoice()
        self.assertEqual(data["paidAmount"], "33.33")
        self.assertEqual(data["outstandingAmount"], "66.67")

    # 13. fields read-only
    def test_fields_are_read_only_on_patch(self):
        response = self.client.patch(
            f"/invoices/{self.invoice.id}",
            {"paidAmount": "999999.00", "outstandingAmount": "0.00", "notes": "attempted override"},
            format="json",
        )
        # PATCH is draft-only; this invoice is already sent -> 409, proving
        # nothing about paidAmount, but also proves it never silently
        # succeeded via smuggled fields. Assert directly against the
        # persisted aggregate afterward regardless of status code.
        self.assertIn(response.status_code, (status.HTTP_200_OK, status.HTTP_409_CONFLICT))

        data = self._get_invoice()
        self.assertEqual(data["paidAmount"], "0.00")
        self.assertEqual(data["outstandingAmount"], "100.00")

    def test_fields_are_read_only_on_draft_patch(self):
        draft = InvoiceService.create_invoice(
            project=self.project1,
            items=[{"description": "Draft item", "quantity": Decimal("1.00"), "rate": Decimal("80.00")}],
        )
        response = self.client.patch(
            f"/invoices/{draft.id}",
            {"paidAmount": "999999.00", "outstandingAmount": "0.00"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()["data"]
        self.assertEqual(data["paidAmount"], "0.00")
        self.assertEqual(data["outstandingAmount"], "80.00")

    # 14. invoice detail includes aggregates
    def test_detail_includes_aggregates(self):
        data = self._get_invoice()
        self.assertIn("paidAmount", data)
        self.assertIn("outstandingAmount", data)

    # 15. invoice list includes aggregates (same serializer contract)
    def test_list_includes_aggregates(self):
        self.client.post(
            f"/invoices/{self.invoice.id}/payments", {"paymentDate": "2026-09-01", "amount": "15.00"}, format="json"
        )
        response = self.client.get(f"/projects/{self.project1.id}/invoices")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        rows = response.json()["data"]
        row = next(r for r in rows if r["id"] == str(self.invoice.id))
        self.assertEqual(row["paidAmount"], "15.00")
        self.assertEqual(row["outstandingAmount"], "85.00")

    # 16. cancelled/draft behavior matches current rules
    def test_draft_invoice_zero_aggregate(self):
        draft = InvoiceService.create_invoice(
            project=self.project1,
            items=[{"description": "Draft item", "quantity": Decimal("1.00"), "rate": Decimal("70.00")}],
        )
        response = self.client.get(f"/invoices/{draft.id}")
        data = response.json()["data"]
        self.assertEqual(data["status"], "draft")
        self.assertEqual(data["paidAmount"], "0.00")
        self.assertEqual(data["outstandingAmount"], "70.00")

    def test_cancelled_invoice_retains_historical_paid_amount(self):
        """
        A partially_paid invoice can be cancelled (CANCELLABLE_STATUSES);
        its prior real payments don't vanish, and the aggregate must stay
        mathematically consistent even though the invoice can no longer
        accept new payments.
        """
        self.client.post(
            f"/invoices/{self.invoice.id}/payments", {"paymentDate": "2026-09-01", "amount": "40.00"}, format="json"
        )
        self.client.post(f"/invoices/{self.invoice.id}/cancel", {}, format="json")

        data = self._get_invoice()
        self.assertEqual(data["status"], "cancelled")
        self.assertEqual(data["paidAmount"], "40.00")
        self.assertEqual(data["outstandingAmount"], "60.00")

        # cancelled invoices cannot accept new payments -- existing rule,
        # not something this task changes.
        response = self.client.post(
            f"/invoices/{self.invoice.id}/payments", {"paymentDate": "2026-09-03", "amount": "10.00"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)

    # 17. status remains consistent (covered across tests above; one
    # direct assertion that status is never derived from amounts here)
    def test_status_is_the_real_persisted_derived_value_not_reconstructed(self):
        data = self._get_invoice()
        self.assertEqual(data["status"], InvoiceService.compute_effective_status(self.invoice))

    # 18. soft-deleted payment excluded (same as voided -- Payment has no
    # separate status field, deleted_at alone distinguishes it)
    def test_soft_deleted_payment_excluded_from_aggregate(self):
        payment = Payment.objects.create(
            company=self.company1,
            invoice=self.invoice,
            client=self.client1,
            project=self.project1,
            payment_date="2026-09-01",
            amount=Decimal("50.00"),
        )
        self.assertEqual(self._get_invoice()["paidAmount"], "50.00")

        payment.delete()  # soft-delete

        self.assertEqual(self._get_invoice()["paidAmount"], "0.00")

    # 19. no frontend-style recomputation required -- the response already
    # carries the final number with no further math needed by any caller.
    def test_outstanding_is_exactly_total_minus_paid_when_not_overpaid(self):
        self.client.post(
            f"/invoices/{self.invoice.id}/payments", {"paymentDate": "2026-09-01", "amount": "37.50"}, format="json"
        )
        data = self._get_invoice()
        self.assertEqual(
            Decimal(data["outstandingAmount"]),
            Decimal(data["total"]) - Decimal(data["paidAmount"]),
        )

    # 20. N+1 regression protection
    def test_list_does_not_incur_n_plus_1_payment_queries(self):
        """
        Isolates the payment-aggregate query cost specifically: holds the
        invoice (and item) count in the list fixed across both captures,
        varying only whether each invoice has a payment recorded against
        it. A naive per-invoice `sum_active_amount_for_invoice` call in the
        serializer would add one extra SUM query per invoice once payments
        exist; the Subquery annotation must not. (Comparing against a
        totally payment-free baseline would also pick up this app's
        pre-existing, unrelated-to-payments `items` nested-serializer
        query per invoice -- holding invoice count constant cancels that
        out, isolating exactly the payments concern this task owns.)
        """
        from django.test.utils import CaptureQueriesContext
        from django.db import connection

        extra_invoices = []
        for i in range(5):
            invoice = InvoiceService.create_invoice(
                project=self.project1,
                items=[{"description": f"Item {i}", "quantity": Decimal("1.00"), "rate": Decimal("10.00")}],
            )
            InvoiceService.send_invoice(invoice)
            invoice.refresh_from_db()
            extra_invoices.append(invoice)

        with CaptureQueriesContext(connection) as ctx_before:
            response_before = self.client.get(f"/projects/{self.project1.id}/invoices")
        self.assertEqual(response_before.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response_before.json()["data"]), 6)
        queries_with_no_payments = len(ctx_before.captured_queries)

        for invoice in extra_invoices:
            PaymentService.create_payment(invoice=invoice, payment_date="2026-09-01", amount=Decimal("5.00"))

        with CaptureQueriesContext(connection) as ctx_after:
            response_after = self.client.get(f"/projects/{self.project1.id}/invoices")
        self.assertEqual(response_after.status_code, status.HTTP_200_OK)
        queries_with_payments = len(ctx_after.captured_queries)

        rows = response_after.json()["data"]
        self.assertEqual(len(rows), 6)  # self.invoice + 5 new ones
        for row in rows:
            if row["id"] != str(self.invoice.id):
                self.assertEqual(row["paidAmount"], "5.00")

        self.assertEqual(
            queries_with_no_payments,
            queries_with_payments,
            "Invoice list query count must not grow once invoices in the list have payments "
            f"(no payments: {queries_with_no_payments} queries, with payments: {queries_with_payments} queries) "
            "-- the paid_amount subquery must fold into the single list query, never one SUM per invoice.",
        )


class InvoicePaymentAggregateComputationTestCase(TestCase):
    """
    Unit-level coverage of InvoiceService.get_paid_amount/
    compute_outstanding_amount directly, independent of the HTTP layer --
    covers the annotated-vs-unannotated instance fallback explicitly.
    """

    def setUp(self):
        self.company = Company.objects.create(name="Direct Co", status=CompanyStatus.ACTIVE)
        self.client_obj = Client.objects.create(company=self.company, name="Direct Client")
        self.project = Project.objects.create(company=self.company, client=self.client_obj, name="Direct Project")

    def test_get_paid_amount_uses_annotation_when_present(self):
        invoice = InvoiceService.create_invoice(
            project=self.project,
            items=[{"description": "X", "quantity": Decimal("1.00"), "rate": Decimal("100.00")}],
        )
        InvoiceService.send_invoice(invoice)
        invoice.refresh_from_db()
        PaymentService.create_payment(invoice=invoice, payment_date="2026-09-01", amount=Decimal("42.00"))

        annotated = InvoiceService.get_invoice_by_id(invoice.id)
        self.assertTrue(hasattr(annotated, "paid_amount"))
        self.assertEqual(InvoiceService.get_paid_amount(annotated), Decimal("42.00"))

    def test_get_paid_amount_falls_back_when_not_annotated(self):
        invoice = InvoiceService.create_invoice(
            project=self.project,
            items=[{"description": "X", "quantity": Decimal("1.00"), "rate": Decimal("100.00")}],
        )
        InvoiceService.send_invoice(invoice)
        invoice.refresh_from_db()
        PaymentService.create_payment(invoice=invoice, payment_date="2026-09-01", amount=Decimal("18.00"))

        # `invoice` here is a plain, non-annotated instance (create_invoice/
        # send_invoice never re-fetch through the repository) -- exactly
        # the fallback path.
        self.assertFalse(hasattr(invoice, "paid_amount"))
        invoice.refresh_from_db()
        self.assertFalse(hasattr(invoice, "paid_amount"))
        self.assertEqual(InvoiceService.get_paid_amount(invoice), Decimal("18.00"))

    def test_compute_outstanding_amount_floors_at_zero(self):
        invoice = InvoiceService.create_invoice(
            project=self.project,
            items=[{"description": "X", "quantity": Decimal("1.00"), "rate": Decimal("100.00")}],
        )
        InvoiceService.send_invoice(invoice)
        invoice.refresh_from_db()
        PaymentService.create_payment(invoice=invoice, payment_date="2026-09-01", amount=Decimal("150.00"))

        annotated = InvoiceService.get_invoice_by_id(invoice.id)
        self.assertEqual(InvoiceService.compute_outstanding_amount(annotated), Decimal("0.00"))
