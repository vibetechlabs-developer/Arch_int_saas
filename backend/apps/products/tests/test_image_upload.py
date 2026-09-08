import io
import shutil
import tempfile
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from PIL import Image
from rest_framework import status
from rest_framework.test import APIClient

from apps.authentication.tokens import CompanyUserAccessToken
from apps.common.test_utils import make_full_access_membership
from apps.company.models import Company, CompanyStatus
from apps.products.models import Product, ProductCategory, ProductSubcategory
from apps.users.models import CompanyMembership, CompanyMembershipStatus

User = get_user_model()


def _synthetic_image_bytes(fmt: str) -> bytes:
    """A tiny (2x2) genuinely-decodable image in the given Pillow format."""
    buffer = io.BytesIO()
    Image.new("RGB", (2, 2), color=(200, 100, 50)).save(buffer, format=fmt)
    return buffer.getvalue()


_TEMP_MEDIA_ROOT = tempfile.mkdtemp(prefix="product_image_upload_tests_")


@override_settings(MEDIA_ROOT=_TEMP_MEDIA_ROOT)
class ProductImageUploadViewTestCase(TestCase):
    """
    Integration test suite for `POST /products/images/upload`. Uses a
    throwaway MEDIA_ROOT (cleaned up in tearDownClass) so test runs never
    write into the real development media/ directory.
    """

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(_TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        # Django's test client defaults to Host: testserver, which Django's
        # own URLValidator rejects (no dot, not "localhost") — a real dev/
        # prod request always carries a real host, so this only affects the
        # test environment, not the production code path.
        self.client = APIClient(SERVER_NAME="localhost")

        self.member_user = User.objects.create_user(
            email="alice@company1.com", name="Alice Member", password="StrongPassword123!"
        )
        self.member_token = str(CompanyUserAccessToken.for_user(self.member_user))

        self.no_permission_user = User.objects.create_user(
            email="dave@company1.com", name="Dave NoPerm", password="StrongPassword123!"
        )
        self.no_permission_token = str(CompanyUserAccessToken.for_user(self.no_permission_user))

        self.company1 = Company.objects.create(name="Studio One", status=CompanyStatus.ACTIVE)
        make_full_access_membership(self.company1, self.member_user)
        # Active membership, deliberately no role -> zero permission codes.
        CompanyMembership.objects.create(
            company=self.company1, user=self.no_permission_user, status=CompanyMembershipStatus.ACTIVE
        )

        self.category = ProductCategory.objects.create(company=self.company1, name="Flooring")
        self.subcategory = ProductSubcategory.objects.create(
            company=self.company1, category=self.category, name="Tiles"
        )

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.member_token}")

    def _upload(self, content: bytes, filename: str = "photo.jpg", content_type: str = "image/jpeg"):
        upload = SimpleUploadedFile(filename, content, content_type=content_type)
        return self.client.post("/products/images/upload", {"image": upload}, format="multipart")

    # --- Auth / permission ------------------------------------------------

    def test_unauthenticated_upload_rejected_401(self):
        self.client.credentials()
        response = self._upload(_synthetic_image_bytes("JPEG"))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_upload_without_product_manage_permission_rejected_403(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.no_permission_token}")
        response = self._upload(_synthetic_image_bytes("JPEG"))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    # --- Valid formats ------------------------------------------------------

    def test_valid_jpeg_upload_succeeds(self):
        response = self._upload(_synthetic_image_bytes("JPEG"), "photo.jpg", "image/jpeg")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        data = response.json()["data"]
        self.assertTrue(data["url"].startswith("http"))
        self.assertEqual(data["contentType"], "image/jpeg")

    def test_valid_png_upload_succeeds(self):
        response = self._upload(_synthetic_image_bytes("PNG"), "photo.png", "image/png")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.json()["data"]["contentType"], "image/png")

    def test_valid_webp_upload_succeeds(self):
        response = self._upload(_synthetic_image_bytes("WEBP"), "photo.webp", "image/webp")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.json()["data"]["contentType"], "image/webp")

    # --- Validation -----------------------------------------------------

    def test_unsupported_format_rejected(self):
        response = self._upload(_synthetic_image_bytes("GIF"), "photo.gif", "image/gif")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json()["error"]["code"], "VALIDATION_ERROR")

    def test_oversized_image_rejected(self):
        oversized = b"a" * (6 * 1024 * 1024)
        response = self._upload(oversized)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("5 MB", response.json()["error"]["details"][0]["issue"])

    def test_fake_extension_with_non_image_content_rejected(self):
        """A `.jpg` filename with plain-text bytes must fail on real content, not pass on the extension."""
        response = self._upload(b"not actually an image", "totally-a-photo.jpg", "image/jpeg")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_missing_file_rejected(self):
        response = self.client.post("/products/images/upload", {}, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # --- Tenant safety / response shape ----------------------------------

    def test_response_url_scoped_to_uploader_company(self):
        response = self._upload(_synthetic_image_bytes("PNG"), "photo.png", "image/png")
        self.assertIn(f"products/{self.company1.id}/", response.json()["data"]["url"])

    # --- Product integration ---------------------------------------------

    def test_uploaded_url_can_be_persisted_and_retrieved_on_a_product(self):
        upload_response = self._upload(_synthetic_image_bytes("JPEG"), "photo.jpg", "image/jpeg")
        uploaded_url = upload_response.json()["data"]["url"]

        create_response = self.client.post(
            "/products",
            {
                "name": "Ceramic Tile",
                "subcategoryId": str(self.subcategory.id),
                "imageUrl": uploaded_url,
            },
        )
        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)
        product_id = create_response.json()["data"]["id"]
        self.assertEqual(create_response.json()["data"]["imageUrl"], uploaded_url)

        retrieve_response = self.client.get(f"/products/{product_id}")
        self.assertEqual(retrieve_response.status_code, status.HTTP_200_OK)
        self.assertEqual(retrieve_response.json()["data"]["imageUrl"], uploaded_url)

    def test_product_image_can_be_removed_via_empty_imageurl(self):
        """
        Pre-existing backend behavior (ProductService.update_product already
        treats `imageUrl: ""` as "clear it") — confirmed here as part of
        this feature's Remove Image support, not a new backend change.
        """
        product = Product.objects.create(
            company=self.company1,
            subcategory=self.subcategory,
            name="Ceramic Tile",
            image_url="https://files.example.com/old.jpg",
        )

        response = self.client.patch(f"/products/{product.id}", {"imageUrl": ""}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["data"]["imageUrl"], "")
