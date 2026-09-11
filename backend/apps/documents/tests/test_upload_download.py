import shutil
import tempfile

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from rest_framework import status
from rest_framework.test import APIClient

from apps.authentication.tokens import CompanyUserAccessToken
from apps.clients.models import Client
from apps.common.test_utils import make_full_access_membership
from apps.company.models import Company, CompanyStatus
from apps.documents.models import Document
from apps.projects.models import Project
from apps.users.models import CompanyMembership, CompanyMembershipStatus

User = get_user_model()

_TEMP_PRIVATE_ROOT = tempfile.mkdtemp(prefix="document_upload_tests_private_")
_TEST_STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "private": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
        "OPTIONS": {"location": _TEMP_PRIVATE_ROOT, "base_url": None},
    },
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}


@override_settings(STORAGES=_TEST_STORAGES)
class DocumentUploadDownloadTestCase(TestCase):
    """
    Integration test suite for `POST /documents/upload` and
    `GET /documents/{id}/download` (BE-078) -- the real multipart upload
    path, private storage isolation, and tenant/RBAC-gated access. Uses a
    throwaway private-storage directory (cleaned up in tearDownClass) so
    test runs never touch the real dev media_private/ directory.
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

    def _upload_file(self, content: bytes = b"%PDF-1.4\nfake pdf body", filename: str = "doc.pdf"):
        upload = SimpleUploadedFile(filename, content, content_type="application/pdf")
        return self.client.post("/documents/upload", {"file": upload}, format="multipart")

    # --- Upload -------------------------------------------------------------

    def test_unauthenticated_upload_rejected_401(self):
        self.client.credentials()
        response = self._upload_file()
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_upload_without_document_manage_rejected_403(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.no_permission_token}")
        response = self._upload_file()
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_valid_pdf_upload_returns_key_no_url(self):
        response = self._upload_file()
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        data = response.json()["data"]
        self.assertIn("key", data)
        self.assertNotIn("url", data)
        self.assertTrue(data["key"].startswith(f"documents/{self.company1.id}/"))

    def test_html_disguised_as_pdf_rejected(self):
        response = self._upload_file(b"<html><script>alert(1)</script></html>", "fake.pdf")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # --- Register (create) with a real uploaded file ------------------------

    def test_create_document_with_storage_key_omits_file_url_and_marks_has_stored_file(self):
        uploaded = self._upload_file().json()["data"]
        response = self.client.post(
            f"/projects/{self.project1.id}/documents",
            {"fileStorageKey": uploaded["key"]},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        data = response.json()["data"]
        self.assertEqual(data["fileUrl"], "")
        self.assertTrue(data["hasStoredFile"])

    def test_create_document_with_both_url_and_key_rejected(self):
        uploaded = self._upload_file().json()["data"]
        response = self.client.post(
            f"/projects/{self.project1.id}/documents",
            {"fileUrl": "https://files.example.com/doc.pdf", "fileStorageKey": uploaded["key"]},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_legacy_url_only_document_reports_has_stored_file_false(self):
        response = self.client.post(
            f"/projects/{self.project1.id}/documents",
            {"fileUrl": "https://files.example.com/legacy.pdf"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertFalse(response.json()["data"]["hasStoredFile"])

    # --- Download -------------------------------------------------------------

    def test_download_streams_real_file_content(self):
        content = b"%PDF-1.4\nreal document body for download test"
        uploaded = self._upload_file(content).json()["data"]
        create_response = self.client.post(
            f"/projects/{self.project1.id}/documents",
            {"fileStorageKey": uploaded["key"]},
            format="json",
        )
        document_id = create_response.json()["data"]["id"]

        response = self.client.get(f"/documents/{document_id}/download")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        streamed = b"".join(response.streaming_content)
        self.assertEqual(streamed, content)

    def test_download_unauthenticated_rejected_401(self):
        uploaded = self._upload_file().json()["data"]
        create_response = self.client.post(
            f"/projects/{self.project1.id}/documents", {"fileStorageKey": uploaded["key"]}, format="json"
        )
        document_id = create_response.json()["data"]["id"]

        self.client.credentials()
        response = self.client.get(f"/documents/{document_id}/download")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_download_cross_tenant_rejected_404(self):
        uploaded = self._upload_file().json()["data"]
        create_response = self.client.post(
            f"/projects/{self.project1.id}/documents", {"fileStorageKey": uploaded["key"]}, format="json"
        )
        document_id = create_response.json()["data"]["id"]

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.other_company_token}")
        response = self.client.get(f"/documents/{document_id}/download")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_download_legacy_url_only_document_returns_404(self):
        document = Document.objects.create(
            company=self.company1,
            project=self.project1,
            entity_type="project",
            entity_id=self.project1.id,
            file_url="https://files.example.com/legacy.pdf",
        )
        response = self.client.get(f"/documents/{document.id}/download")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_soft_deleted_document_file_is_not_physically_removed(self):
        """
        BE-078 storage policy: a document's stored file is compliance/
        audit-relevant and is never physically deleted just because the
        row itself was soft-deleted.
        """
        from apps.common.storage import private_file_exists

        uploaded = self._upload_file().json()["data"]
        create_response = self.client.post(
            f"/projects/{self.project1.id}/documents", {"fileStorageKey": uploaded["key"]}, format="json"
        )
        document_id = create_response.json()["data"]["id"]

        delete_response = self.client.delete(f"/documents/{document_id}")
        self.assertEqual(delete_response.status_code, status.HTTP_200_OK)
        self.assertTrue(private_file_exists("documents", uploaded["key"]))
