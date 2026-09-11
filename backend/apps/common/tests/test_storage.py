"""
Unit tests for the shared storage abstraction (BE-078,
apps.common.storage). Uses a throwaway MEDIA_ROOT/private-storage
directory (cleaned up in tearDownClass) so test runs never touch the
real development media/ directories, and never hit real S3 -- these are
pure local-backend tests plus settings-level S3 configuration checks (see
apps/common/tests/test_settings_hardening.py for STORAGE_BACKEND=s3 boot
verification).
"""

import io
import shutil
import tempfile

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase, override_settings
from PIL import Image
from rest_framework import exceptions as drf_exceptions

from apps.common import storage as storage_service

_TEMP_MEDIA_ROOT = tempfile.mkdtemp(prefix="storage_core_tests_media_")
_TEMP_PRIVATE_ROOT = tempfile.mkdtemp(prefix="storage_core_tests_private_")

_TEST_STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
        "OPTIONS": {"location": _TEMP_MEDIA_ROOT, "base_url": "/media/"},
    },
    "private": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
        "OPTIONS": {"location": _TEMP_PRIVATE_ROOT, "base_url": None},
    },
}


def _image_bytes(fmt: str) -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (2, 2), color=(10, 20, 30)).save(buffer, format=fmt)
    return buffer.getvalue()


@override_settings(STORAGES=_TEST_STORAGES)
class StorageScopeTestCase(SimpleTestCase):
    """Scope classification and key-generation behavior."""

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(_TEMP_MEDIA_ROOT, ignore_errors=True)
        shutil.rmtree(_TEMP_PRIVATE_ROOT, ignore_errors=True)

    def test_public_scopes_are_products_and_companies(self):
        self.assertEqual(storage_service.PUBLIC_SCOPES, frozenset({"products", "companies"}))

    def test_private_scopes_are_documents_expenses_payments(self):
        self.assertEqual(
            storage_service.PRIVATE_SCOPES, frozenset({"documents", "expenses", "payments"})
        )

    def test_unknown_scope_raises(self):
        with self.assertRaises(ValueError):
            storage_service._storage_for_scope("not-a-real-scope")

    def test_generate_storage_key_is_tenant_namespaced_and_unique(self):
        company_id = "11111111-1111-1111-1111-111111111111"
        key1 = storage_service.generate_storage_key("products", company_id, "jpg")
        key2 = storage_service.generate_storage_key("products", company_id, "jpg")
        self.assertTrue(key1.startswith(f"products/{company_id}/"))
        self.assertTrue(key1.endswith(".jpg"))
        self.assertNotEqual(key1, key2)

    def test_public_url_rejects_private_scope(self):
        with self.assertRaises(ValueError):
            storage_service.public_url("documents", "documents/x/y.pdf")

    def test_private_signed_url_rejects_public_scope(self):
        with self.assertRaises(ValueError):
            storage_service.private_signed_url("products", "products/x/y.jpg")

    def test_open_private_file_rejects_public_scope(self):
        with self.assertRaises(ValueError):
            storage_service.open_private_file("companies", "companies/x/y.png")


@override_settings(STORAGES=_TEST_STORAGES)
class SaveAndDeleteFileTestCase(SimpleTestCase):
    """save_upload / delete_file round-trip and safety behavior."""

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(_TEMP_MEDIA_ROOT, ignore_errors=True)
        shutil.rmtree(_TEMP_PRIVATE_ROOT, ignore_errors=True)

    def test_save_upload_public_scope_then_delete(self):
        upload = SimpleUploadedFile("logo.png", _image_bytes("PNG"), content_type="image/png")
        key = storage_service.generate_storage_key("companies", "c1", "png")
        saved_path = storage_service.save_upload("companies", key, upload)
        self.assertEqual(saved_path, key)

        url = storage_service.public_url("companies", key)
        self.assertIn(key, url)

        storage_service.delete_file("companies", key)
        # Idempotent -- deleting an already-gone key must not raise.
        storage_service.delete_file("companies", key)

    def test_save_upload_private_scope_then_open(self):
        upload = SimpleUploadedFile("receipt.pdf", b"%PDF-1.4 fake pdf body", content_type="application/pdf")
        key = storage_service.generate_storage_key("expenses", "c1", "pdf")
        storage_service.save_upload("expenses", key, upload)

        with storage_service.open_private_file("expenses", key) as f:
            content = f.read()
        self.assertIn(b"%PDF-1.4", content)

        storage_service.delete_file("expenses", key)

    def test_delete_file_blank_key_is_a_safe_noop(self):
        # Must never attempt to delete "nothing" -- a blank key means this
        # app never uploaded anything under this reference to begin with.
        storage_service.delete_file("products", "")
        storage_service.delete_file("products", None)

    def test_delete_file_swallows_backend_errors(self):
        # A key that was never saved -- delete_file must not raise even
        # though the underlying backend may raise internally.
        storage_service.delete_file("products", "products/does/not/exist.jpg")


@override_settings(STORAGES=_TEST_STORAGES)
class ValidateImageUploadTestCase(SimpleTestCase):
    """Shared PUBLIC-image validator (Product images, Company logos)."""

    def test_valid_jpeg_accepted(self):
        upload = SimpleUploadedFile("a.jpg", _image_bytes("JPEG"), content_type="image/jpeg")
        extension, content_type = storage_service.validate_image_upload(upload)
        self.assertEqual((extension, content_type), ("jpg", "image/jpeg"))

    def test_valid_png_accepted(self):
        upload = SimpleUploadedFile("a.png", _image_bytes("PNG"), content_type="image/png")
        extension, content_type = storage_service.validate_image_upload(upload)
        self.assertEqual((extension, content_type), ("png", "image/png"))

    def test_valid_webp_accepted(self):
        upload = SimpleUploadedFile("a.webp", _image_bytes("WEBP"), content_type="image/webp")
        extension, content_type = storage_service.validate_image_upload(upload)
        self.assertEqual((extension, content_type), ("webp", "image/webp"))

    def test_none_file_rejected(self):
        with self.assertRaises(drf_exceptions.ValidationError):
            storage_service.validate_image_upload(None)

    def test_oversized_rejected(self):
        upload = SimpleUploadedFile("a.jpg", b"a" * (6 * 1024 * 1024), content_type="image/jpeg")
        with self.assertRaises(drf_exceptions.ValidationError):
            storage_service.validate_image_upload(upload)

    def test_empty_file_rejected(self):
        upload = SimpleUploadedFile("a.jpg", b"", content_type="image/jpeg")
        with self.assertRaises(drf_exceptions.ValidationError):
            storage_service.validate_image_upload(upload)

    def test_unsupported_format_rejected(self):
        upload = SimpleUploadedFile("a.gif", _image_bytes("GIF"), content_type="image/gif")
        with self.assertRaises(drf_exceptions.ValidationError):
            storage_service.validate_image_upload(upload)

    def test_fake_extension_non_image_content_rejected(self):
        upload = SimpleUploadedFile("a.jpg", b"not an image at all", content_type="image/jpeg")
        with self.assertRaises(drf_exceptions.ValidationError):
            storage_service.validate_image_upload(upload)


@override_settings(STORAGES=_TEST_STORAGES)
class ValidateDocumentUploadTestCase(SimpleTestCase):
    """Shared PRIVATE-document validator (documents, expense/payment receipts)."""

    def test_real_pdf_signature_accepted(self):
        upload = SimpleUploadedFile("f.pdf", b"%PDF-1.4\n%rest of a fake pdf body", content_type="application/pdf")
        extension, content_type = storage_service.validate_document_upload(upload)
        self.assertEqual((extension, content_type), ("pdf", "application/pdf"))

    def test_valid_jpeg_accepted(self):
        upload = SimpleUploadedFile("f.jpg", _image_bytes("JPEG"), content_type="image/jpeg")
        extension, content_type = storage_service.validate_document_upload(upload)
        self.assertEqual((extension, content_type), ("jpg", "image/jpeg"))

    def test_html_disguised_as_pdf_rejected(self):
        """The exact case Phase 7's 'no HTML/JS uploads' rule targets."""
        upload = SimpleUploadedFile(
            "fake.pdf", b"<html><script>alert(1)</script></html>", content_type="application/pdf"
        )
        with self.assertRaises(drf_exceptions.ValidationError):
            storage_service.validate_document_upload(upload)

    def test_executable_disguised_as_pdf_rejected(self):
        upload = SimpleUploadedFile("fake.pdf", b"MZ\x90\x00\x03\x00\x00\x00", content_type="application/pdf")
        with self.assertRaises(drf_exceptions.ValidationError):
            storage_service.validate_document_upload(upload)

    def test_oversized_rejected(self):
        upload = SimpleUploadedFile(
            "big.pdf", b"%PDF-" + b"a" * (21 * 1024 * 1024), content_type="application/pdf"
        )
        with self.assertRaises(drf_exceptions.ValidationError):
            storage_service.validate_document_upload(upload)

    def test_empty_file_rejected(self):
        upload = SimpleUploadedFile("f.pdf", b"", content_type="application/pdf")
        with self.assertRaises(drf_exceptions.ValidationError):
            storage_service.validate_document_upload(upload)

    def test_none_file_rejected(self):
        with self.assertRaises(drf_exceptions.ValidationError):
            storage_service.validate_document_upload(None)


class SafeDisplayFilenameTestCase(SimpleTestCase):
    def test_strips_directory_components(self):
        self.assertEqual(storage_service.safe_display_filename("../../etc/passwd.jpg"), "passwd.jpg")

    def test_blank_name_falls_back(self):
        self.assertEqual(storage_service.safe_display_filename(""), "file")

    def test_truncates_long_names(self):
        long_name = "a" * 400 + ".jpg"
        self.assertLessEqual(len(storage_service.safe_display_filename(long_name)), 255)
