import shutil
import tempfile
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from rest_framework import status
from rest_framework.test import APIClient

from apps.authentication.tokens import CompanyUserAccessToken
from apps.clients.models import Client
from apps.common.test_utils import make_full_access_membership
from apps.company.models import Company, CompanyStatus
from apps.invoices.services import InvoiceService
from apps.payments.models import Payment
from apps.projects.models import Project
from apps.users.models import CompanyMembership, CompanyMembershipStatus

User = get_user_model()

_TEMP_PRIVATE_ROOT = tempfile.mkdtemp(prefix="payment_receipt_tests_private_")
_TEST_STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "private": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
        "OPTIONS": {"location": _TEMP_PRIVATE_ROOT, "base_url": None},
    },
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}


@override_settings(STORAGES=_TEST_STORAGES)
class PaymentReceiptUploadDownloadTestCase(TestCase):
    """
    Integration test suite for `POST /payments/receipts/upload` and
    `GET /payments/{id}/receipt` (BE-078). Payment has no update endpoint
    (create + void only), so a receipt is only ever attached at creation
    -- these tests also confirm that never touches financial fields.
    """

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(_TEMP_PRIVATE_ROOT, ignore_errors=True)

    def setUp(self):
        self.client = APIClient()

        self.member_user = User.objects.create_user(
            email="alice@company1.com", name="Alice Member", password="StrongPassword123!"
        )
        self.member_token = str(CompanyUserAccessToken.for_user(self.member_user))

        self.no_permission_user = User.objects.create_user(
            email="dave@company1.com", name="Dave NoPerm", password="StrongPassword123!"
        )
        self.no_permission_token = str(CompanyUserAccessToken.for_user(self.no_permission_user))

        self.other_company_user = User.objects.create_user(
            email="eve@company2.com", name="Eve Other", password="StrongPassword123!"
        )
        self.other_company_token = str(CompanyUserAccessToken.for_user(self.other_company_user))

        self.company1 = Company.objects.create(name="Studio One", status=CompanyStatus.ACTIVE)
        self.company2 = Company.objects.create(name="Studio Two", status=CompanyStatus.ACTIVE)
        make_full_access_membership(self.company1, self.member_user)
        make_full_access_membership(self.company2, self.other_company_user)
        CompanyMembership.objects.create(
            company=self.company1, user=self.no_permission_user, status=CompanyMembershipStatus.ACTIVE
        )

        self.client1 = Client.objects.create(company=self.company1, name="Client One")
        self.project1 = Project.objects.create(
            company=self.company1, client=self.client1, name="Kitchen Remodel"
        )
        self.invoice = InvoiceService.create_invoice(
            project=self.project1,
            items=[{"description": "X", "quantity": Decimal("1.00"), "rate": Decimal("500.00")}],
        )
        InvoiceService.send_invoice(self.invoice)
        self.invoice.refresh_from_db()

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.member_token}")

    def _upload_receipt(self, content: bytes = b"%PDF-1.4\nreceipt body", filename: str = "receipt.pdf"):
        upload = SimpleUploadedFile(filename, content, content_type="application/pdf")
        return self.client.post("/payments/receipts/upload", {"file": upload}, format="multipart")

    def test_unauthenticated_upload_rejected_401(self):
        self.client.credentials()
        response = self._upload_receipt()
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_upload_without_payment_create_rejected_403(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.no_permission_token}")
        response = self._upload_receipt()
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_valid_upload_returns_key_no_url(self):
        response = self._upload_receipt()
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        data = response.json()["data"]
        self.assertIn("key", data)
        self.assertNotIn("url", data)
        self.assertTrue(data["key"].startswith(f"payments/{self.company1.id}/"))

    def test_create_payment_with_receipt_storage_key_leaves_amount_authoritative(self):
        uploaded = self._upload_receipt().json()["data"]
        response = self.client.post(
            f"/invoices/{self.invoice.id}/payments",
            {"paymentDate": "2026-09-01", "amount": "500.00", "receiptStorageKey": uploaded["key"]},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        data = response.json()["data"]
        self.assertEqual(data["amount"], "500.00")
        self.assertEqual(data["receiptUrl"], "")
        self.assertTrue(data["hasStoredReceipt"])

    def test_create_payment_with_both_receipt_url_and_key_rejected(self):
        uploaded = self._upload_receipt().json()["data"]
        response = self.client.post(
            f"/invoices/{self.invoice.id}/payments",
            {
                "paymentDate": "2026-09-01",
                "amount": "500.00",
                "receiptUrl": "https://files.example.com/r.pdf",
                "receiptStorageKey": uploaded["key"],
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_download_streams_real_receipt_content(self):
        content = b"%PDF-1.4\nreal payment receipt"
        uploaded = self._upload_receipt(content).json()["data"]
        create_response = self.client.post(
            f"/invoices/{self.invoice.id}/payments",
            {"paymentDate": "2026-09-01", "amount": "500.00", "receiptStorageKey": uploaded["key"]},
            format="json",
        )
        payment_id = create_response.json()["data"]["id"]

        response = self.client.get(f"/payments/{payment_id}/receipt")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(b"".join(response.streaming_content), content)

    def test_download_cross_tenant_rejected_404(self):
        uploaded = self._upload_receipt().json()["data"]
        create_response = self.client.post(
            f"/invoices/{self.invoice.id}/payments",
            {"paymentDate": "2026-09-01", "amount": "500.00", "receiptStorageKey": uploaded["key"]},
            format="json",
        )
        payment_id = create_response.json()["data"]["id"]

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.other_company_token}")
        response = self.client.get(f"/payments/{payment_id}/receipt")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_legacy_receipt_url_payment_download_returns_404(self):
        payment = Payment.objects.create(
            company=self.company1,
            invoice=self.invoice,
            client=self.invoice.client,
            project=self.invoice.project,
            payment_date="2026-09-01",
            amount=Decimal("500.00"),
            receipt_url="https://files.example.com/legacy.pdf",
        )
        response = self.client.get(f"/payments/{payment.id}/receipt")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_voiding_payment_does_not_delete_receipt_file(self):
        """BE-078 storage policy: a financial receipt is never physically deleted, even when the payment is voided."""
        from apps.common.storage import private_file_exists

        uploaded = self._upload_receipt().json()["data"]
        create_response = self.client.post(
            f"/invoices/{self.invoice.id}/payments",
            {"paymentDate": "2026-09-01", "amount": "500.00", "receiptStorageKey": uploaded["key"]},
            format="json",
        )
        payment_id = create_response.json()["data"]["id"]

        void_response = self.client.delete(f"/payments/{payment_id}")
        self.assertEqual(void_response.status_code, status.HTTP_200_OK)
        self.assertTrue(private_file_exists("payments", uploaded["key"]))
