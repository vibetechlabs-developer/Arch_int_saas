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
from apps.expenses.models import Expense, ExpenseApprovalStatus
from apps.projects.models import Project
from apps.users.models import CompanyMembership, CompanyMembershipStatus

User = get_user_model()

_TEMP_PRIVATE_ROOT = tempfile.mkdtemp(prefix="expense_receipt_tests_private_")
_TEST_STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "private": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
        "OPTIONS": {"location": _TEMP_PRIVATE_ROOT, "base_url": None},
    },
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}


@override_settings(STORAGES=_TEST_STORAGES)
class ExpenseReceiptUploadDownloadTestCase(TestCase):
    """
    Integration test suite for `POST /expenses/receipts/upload` and
    `GET /expenses/{id}/receipt` (BE-078).
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

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.member_token}")

    def _upload_receipt(self, content: bytes = b"%PDF-1.4\nreceipt body", filename: str = "receipt.pdf"):
        upload = SimpleUploadedFile(filename, content, content_type="application/pdf")
        return self.client.post("/expenses/receipts/upload", {"file": upload}, format="multipart")

    def test_unauthenticated_upload_rejected_401(self):
        self.client.credentials()
        response = self._upload_receipt()
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_upload_without_expense_create_rejected_403(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.no_permission_token}")
        response = self._upload_receipt()
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_valid_upload_returns_key_no_url(self):
        response = self._upload_receipt()
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        data = response.json()["data"]
        self.assertIn("key", data)
        self.assertNotIn("url", data)
        self.assertTrue(data["key"].startswith(f"expenses/{self.company1.id}/"))

    def test_create_expense_with_receipt_storage_key(self):
        uploaded = self._upload_receipt().json()["data"]
        response = self.client.post(
            f"/projects/{self.project1.id}/expenses",
            {
                "amount": "500.00",
                "date": "2026-09-01",
                "receiptStorageKey": uploaded["key"],
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        data = response.json()["data"]
        self.assertEqual(data["receiptUrl"], "")
        self.assertTrue(data["hasStoredReceipt"])

    def test_create_expense_with_both_receipt_url_and_key_rejected(self):
        uploaded = self._upload_receipt().json()["data"]
        response = self.client.post(
            f"/projects/{self.project1.id}/expenses",
            {
                "amount": "500.00",
                "date": "2026-09-01",
                "receiptUrl": "https://files.example.com/r.pdf",
                "receiptStorageKey": uploaded["key"],
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_download_streams_real_receipt_content(self):
        content = b"%PDF-1.4\nreal receipt body"
        uploaded = self._upload_receipt(content).json()["data"]
        create_response = self.client.post(
            f"/projects/{self.project1.id}/expenses",
            {"amount": "500.00", "date": "2026-09-01", "receiptStorageKey": uploaded["key"]},
            format="json",
        )
        expense_id = create_response.json()["data"]["id"]

        response = self.client.get(f"/expenses/{expense_id}/receipt")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(b"".join(response.streaming_content), content)

    def test_download_cross_tenant_rejected_404(self):
        uploaded = self._upload_receipt().json()["data"]
        create_response = self.client.post(
            f"/projects/{self.project1.id}/expenses",
            {"amount": "500.00", "date": "2026-09-01", "receiptStorageKey": uploaded["key"]},
            format="json",
        )
        expense_id = create_response.json()["data"]["id"]

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.other_company_token}")
        response = self.client.get(f"/expenses/{expense_id}/receipt")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_legacy_receipt_url_expense_download_returns_404(self):
        expense = Expense.objects.create(
            company=self.company1,
            project=self.project1,
            amount=Decimal("500.00"),
            date="2026-09-01",
            receipt_url="https://files.example.com/legacy.pdf",
            approval_status=ExpenseApprovalStatus.DRAFT,
        )
        response = self.client.get(f"/expenses/{expense.id}/receipt")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_replacing_receipt_on_draft_expense_does_not_delete_old_file(self):
        """
        BE-078 storage policy: a financial receipt is never automatically
        deleted, even when replaced on a still-draft expense -- unlike a
        Product image or Company logo.
        """
        from apps.common.storage import private_file_exists

        first = self._upload_receipt().json()["data"]
        create_response = self.client.post(
            f"/projects/{self.project1.id}/expenses",
            {"amount": "500.00", "date": "2026-09-01", "receiptStorageKey": first["key"]},
            format="json",
        )
        expense_id = create_response.json()["data"]["id"]

        second = self._upload_receipt().json()["data"]
        response = self.client.patch(
            f"/expenses/{expense_id}",
            {"receiptStorageKey": second["key"]},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(private_file_exists("expenses", first["key"]))
        self.assertTrue(private_file_exists("expenses", second["key"]))
