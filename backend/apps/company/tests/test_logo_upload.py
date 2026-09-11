import io
import shutil
import tempfile

from django.contrib.auth import get_user_model
from django.core.files.storage import storages
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from PIL import Image
from rest_framework import status
from rest_framework.test import APIClient

from apps.authentication.tokens import CompanyUserAccessToken, PlatformAdminAccessToken
from apps.common.test_utils import make_full_access_membership
from apps.company.models import Company, CompanyStatus
from apps.users.models import CompanyMembership, CompanyMembershipStatus

User = get_user_model()


def _synthetic_image_bytes(fmt: str = "PNG") -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (2, 2), color=(50, 80, 120)).save(buffer, format=fmt)
    return buffer.getvalue()


_TEMP_MEDIA_ROOT = tempfile.mkdtemp(prefix="company_logo_upload_tests_")


@override_settings(MEDIA_ROOT=_TEMP_MEDIA_ROOT)
class CompanyLogoUploadViewTestCase(TestCase):
    """
    Integration test suite for `POST /companies/{id}/logo/upload` and its
    downstream effect through `PATCH /companies/{id}` (BE-078). Uses a
    throwaway MEDIA_ROOT (cleaned up in tearDownClass).
    """

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(_TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.client = APIClient(SERVER_NAME="localhost")

        self.superadmin = User.objects.create_superuser(
            email="superadmin@example.com", name="Super Admin", password="StrongPassword123!"
        )
        self.superadmin_token = str(PlatformAdminAccessToken.for_user(self.superadmin))

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

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.member_token}")

    def _upload(self, company_id, content: bytes, filename: str = "logo.png", content_type: str = "image/png"):
        upload = SimpleUploadedFile(filename, content, content_type=content_type)
        return self.client.post(f"/companies/{company_id}/logo/upload", {"logo": upload}, format="multipart")

    def test_unauthenticated_upload_rejected_401(self):
        self.client.credentials()
        response = self._upload(self.company1.id, _synthetic_image_bytes())
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_upload_without_company_manage_permission_rejected_403(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.no_permission_token}")
        response = self._upload(self.company1.id, _synthetic_image_bytes())
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_cross_tenant_upload_rejected_404(self):
        """Error_Handling.md §5: cross-tenant probe by id -> 404, never 403."""
        response = self._upload(self.company2.id, _synthetic_image_bytes())
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_platform_admin_can_upload_for_any_company(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.superadmin_token}")
        response = self._upload(self.company1.id, _synthetic_image_bytes())
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_valid_upload_returns_url_and_key(self):
        response = self._upload(self.company1.id, _synthetic_image_bytes())
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        data = response.json()["data"]
        self.assertTrue(data["url"].startswith("http"))
        self.assertIn(f"companies/{self.company1.id}/", data["key"])

    def test_unsupported_format_rejected(self):
        response = self._upload(self.company1.id, _synthetic_image_bytes("GIF"), "logo.gif", "image/gif")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_uploaded_logo_can_be_persisted_via_company_patch(self):
        uploaded = self._upload(self.company1.id, _synthetic_image_bytes()).json()["data"]

        response = self.client.patch(
            f"/companies/{self.company1.id}",
            {"logoUrl": uploaded["url"], "logoStorageKey": uploaded["key"]},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["data"]["logoUrl"], uploaded["url"])
        self.assertNotIn("logoStorageKey", response.json()["data"])

    def test_replacing_logo_deletes_old_file(self):
        first = self._upload(self.company1.id, _synthetic_image_bytes()).json()["data"]
        self.client.patch(
            f"/companies/{self.company1.id}",
            {"logoUrl": first["url"], "logoStorageKey": first["key"]},
            format="json",
        )
        self.assertTrue(storages["default"].exists(first["key"]))

        second = self._upload(self.company1.id, _synthetic_image_bytes()).json()["data"]
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.patch(
                f"/companies/{self.company1.id}",
                {"logoUrl": second["url"], "logoStorageKey": second["key"]},
                format="json",
            )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(storages["default"].exists(first["key"]))
        self.assertTrue(storages["default"].exists(second["key"]))

    def test_removing_logo_deletes_file(self):
        uploaded = self._upload(self.company1.id, _synthetic_image_bytes()).json()["data"]
        self.client.patch(
            f"/companies/{self.company1.id}",
            {"logoUrl": uploaded["url"], "logoStorageKey": uploaded["key"]},
            format="json",
        )
        self.assertTrue(storages["default"].exists(uploaded["key"]))

        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.patch(
                f"/companies/{self.company1.id}", {"logoUrl": ""}, format="json"
            )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(storages["default"].exists(uploaded["key"]))
