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

from apps.authentication.tokens import CompanyUserAccessToken
from apps.common.test_utils import make_full_access_membership
from apps.company.models import Company, CompanyStatus
from apps.products.models import Product, ProductCategory, ProductSubcategory

User = get_user_model()


def _synthetic_image_bytes(fmt: str = "JPEG") -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (2, 2), color=(200, 100, 50)).save(buffer, format=fmt)
    return buffer.getvalue()


_TEMP_MEDIA_ROOT = tempfile.mkdtemp(prefix="product_image_cleanup_tests_")


@override_settings(MEDIA_ROOT=_TEMP_MEDIA_ROOT)
class ProductImageOrphanCleanupTestCase(TestCase):
    """
    BE-078: replacing/removing a Product's image, when this app actually
    owns the underlying file (a non-blank `imageStorageKey` was tracked
    from a real upload), must delete the superseded file from storage --
    but must NEVER delete a file when the current `imageUrl` was entered
    manually (no storage key on file), since that URL could point
    anywhere and this app never wrote it.
    """

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(_TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.client = APIClient(SERVER_NAME="localhost")
        self.user = User.objects.create_user(
            email="alice@company1.com", name="Alice Member", password="StrongPassword123!"
        )
        self.token = str(CompanyUserAccessToken.for_user(self.user))
        self.company = Company.objects.create(name="Studio One", status=CompanyStatus.ACTIVE)
        make_full_access_membership(self.company, self.user)
        self.category = ProductCategory.objects.create(company=self.company, name="Flooring")
        self.subcategory = ProductSubcategory.objects.create(
            company=self.company, category=self.category, name="Tiles"
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token}")

    def _upload_image(self):
        upload = SimpleUploadedFile("photo.jpg", _synthetic_image_bytes(), content_type="image/jpeg")
        response = self.client.post("/products/images/upload", {"image": upload}, format="multipart")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        return response.json()["data"]

    def test_upload_response_includes_storage_key(self):
        data = self._upload_image()
        self.assertIn("key", data)
        self.assertTrue(data["key"].startswith(f"products/{self.company.id}/"))

    def test_replacing_uploaded_image_deletes_old_file(self):
        first = self._upload_image()
        create_response = self.client.post(
            "/products",
            {
                "name": "Ceramic Tile",
                "subcategoryId": str(self.subcategory.id),
                "imageUrl": first["url"],
                "imageStorageKey": first["key"],
            },
        )
        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)
        product_id = create_response.json()["data"]["id"]
        self.assertTrue(storages["default"].exists(first["key"]))

        second = self._upload_image()
        with self.captureOnCommitCallbacks(execute=True):
            update_response = self.client.patch(
                f"/products/{product_id}",
                {"imageUrl": second["url"], "imageStorageKey": second["key"]},
                format="json",
            )
        self.assertEqual(update_response.status_code, status.HTTP_200_OK)

        self.assertFalse(storages["default"].exists(first["key"]))
        self.assertTrue(storages["default"].exists(second["key"]))

    def test_removing_uploaded_image_deletes_file(self):
        uploaded = self._upload_image()
        create_response = self.client.post(
            "/products",
            {
                "name": "Ceramic Tile",
                "subcategoryId": str(self.subcategory.id),
                "imageUrl": uploaded["url"],
                "imageStorageKey": uploaded["key"],
            },
        )
        product_id = create_response.json()["data"]["id"]
        self.assertTrue(storages["default"].exists(uploaded["key"]))

        with self.captureOnCommitCallbacks(execute=True):
            remove_response = self.client.patch(f"/products/{product_id}", {"imageUrl": ""}, format="json")
        self.assertEqual(remove_response.status_code, status.HTTP_200_OK)
        self.assertFalse(storages["default"].exists(uploaded["key"]))

    def test_manually_entered_url_is_never_deleted_on_replace(self):
        """
        A Product whose imageUrl was typed in manually (no imageStorageKey)
        must never trigger a storage delete when later replaced -- this
        app has no key on file and must not guess one from the URL.
        """
        product = Product.objects.create(
            company=self.company,
            subcategory=self.subcategory,
            name="Ceramic Tile",
            image_url="https://files.example.com/manually-entered.jpg",
        )
        self.assertEqual(product.image_storage_key, "")

        uploaded = self._upload_image()
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.patch(
                f"/products/{product.id}",
                {"imageUrl": uploaded["url"], "imageStorageKey": uploaded["key"]},
                format="json",
            )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Nothing to assert-deleted here (the old URL was never our file to
        # begin with) -- the real assertion is simply that this didn't
        # crash attempting to derive/delete a bogus key, and the new image
        # persists correctly.
        self.assertTrue(storages["default"].exists(uploaded["key"]))

    def test_replacing_with_manual_url_stops_tracking_the_old_key(self):
        """
        Switching FROM an app-owned upload TO a manually-entered URL still
        safely deletes the old (now-superseded) app-owned file, and the
        product's new state correctly carries no storage key.
        """
        first = self._upload_image()
        create_response = self.client.post(
            "/products",
            {
                "name": "Ceramic Tile",
                "subcategoryId": str(self.subcategory.id),
                "imageUrl": first["url"],
                "imageStorageKey": first["key"],
            },
        )
        product_id = create_response.json()["data"]["id"]

        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.patch(
                f"/products/{product_id}",
                {"imageUrl": "https://files.example.com/switched-to-manual.jpg"},
                format="json",
            )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(storages["default"].exists(first["key"]))

        product = Product.objects.get(id=product_id)
        self.assertEqual(product.image_storage_key, "")

    def test_updating_unrelated_field_does_not_touch_image_or_storage(self):
        uploaded = self._upload_image()
        create_response = self.client.post(
            "/products",
            {
                "name": "Ceramic Tile",
                "subcategoryId": str(self.subcategory.id),
                "imageUrl": uploaded["url"],
                "imageStorageKey": uploaded["key"],
            },
        )
        product_id = create_response.json()["data"]["id"]

        response = self.client.patch(f"/products/{product_id}", {"name": "Renamed Tile"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(storages["default"].exists(uploaded["key"]))

        product = Product.objects.get(id=product_id)
        self.assertEqual(product.image_storage_key, uploaded["key"])

    def test_image_storage_key_never_exposed_in_api_responses(self):
        uploaded = self._upload_image()
        create_response = self.client.post(
            "/products",
            {
                "name": "Ceramic Tile",
                "subcategoryId": str(self.subcategory.id),
                "imageUrl": uploaded["url"],
                "imageStorageKey": uploaded["key"],
            },
        )
        self.assertNotIn("imageStorageKey", create_response.json()["data"])

        product_id = create_response.json()["data"]["id"]
        retrieve_response = self.client.get(f"/products/{product_id}")
        self.assertNotIn("imageStorageKey", retrieve_response.json()["data"])
