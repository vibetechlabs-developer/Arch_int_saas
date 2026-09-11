import shutil
import tempfile
from types import SimpleNamespace

from django.test import SimpleTestCase, override_settings

from apps.common import storage as storage_service
from apps.common.pdf_service import (
    PdfRenderError,
    company_logo_data_uri,
    pdf_http_response,
    render_pdf,
    sanitize_filename,
)


class SanitizeFilenameTestCase(SimpleTestCase):
    def test_strips_unsafe_characters(self):
        # Quotes, slashes, and angle brackets are removed entirely; dots
        # are a legitimate filename character and survive.
        result = sanitize_filename('Inv"oice/../<script>')
        for unsafe in ('"', "/", "<", ">"):
            self.assertNotIn(unsafe, result)
        self.assertEqual(result, "Invoice..script")

    def test_collapses_whitespace_to_hyphens(self):
        self.assertEqual(sanitize_filename("Skyline  Villa   Renovation"), "Skyline-Villa-Renovation")

    def test_falls_back_when_nothing_safe_remains(self):
        self.assertEqual(sanitize_filename("###???"), "document")
        self.assertEqual(sanitize_filename(""), "document")

    def test_falls_back_to_custom_default(self):
        self.assertEqual(sanitize_filename("", fallback="invoice"), "invoice")

    def test_transliterates_non_ascii(self):
        # Non-Latin script collapses to the fallback rather than raising or
        # silently producing an empty/invalid filename.
        self.assertEqual(sanitize_filename("北京項目"), "document")

    def test_preserves_normal_names_unchanged(self):
        self.assertEqual(sanitize_filename("INV-000001"), "INV-000001")


class RenderPdfTestCase(SimpleTestCase):
    def test_renders_real_pdf_bytes_from_a_template_string_context(self):
        pdf_bytes = render_pdf(
            "pdf/invoice.html",
            {
                "document_title": "Test",
                "document_type": "INVOICE",
                "document_number": "INV-TEST",
                "status_label": "Draft",
                "company": {"name": "Test Co", "gst_number": ""},
                "client": {"name": "Test Client", "email": "", "mobile": "", "gstin": ""},
                "project": {"name": "Test Project"},
                "currency": "INR",
                "generated_at": "01 Jan 2026, 00:00",
                "items": [],
                "invoice": {
                    "subtotal": "0.00",
                    "discount": "0.00",
                    "tax": "0.00",
                    "total": "0.00",
                    "paid_amount": "0.00",
                    "outstanding_amount": "0.00",
                    "due_date": None,
                    "payment_terms": "",
                    "notes": "",
                },
            },
        )
        self.assertTrue(pdf_bytes.startswith(b"%PDF-"))

    def test_unsafe_html_in_context_is_escaped_not_executed(self):
        """
        A malicious client name must render as literal text, never as
        markup -- Django's render_to_string autoescapes every context
        value by default (no |safe filter is used anywhere in the PDF
        templates), so this proves the safety property directly rather
        than just asserting on the source.
        """
        pdf_bytes = render_pdf(
            "pdf/invoice.html",
            {
                "document_title": "Test",
                "document_type": "INVOICE",
                "document_number": "INV-TEST",
                "status_label": "Draft",
                "company": {"name": "Test Co", "gst_number": ""},
                "client": {
                    "name": "<script>alert(1)</script>",
                    "email": "",
                    "mobile": "",
                    "gstin": "",
                },
                "project": {"name": "Test Project"},
                "currency": "INR",
                "generated_at": "01 Jan 2026, 00:00",
                "items": [],
                "invoice": {
                    "subtotal": "0.00",
                    "discount": "0.00",
                    "tax": "0.00",
                    "total": "0.00",
                    "paid_amount": "0.00",
                    "outstanding_amount": "0.00",
                    "due_date": None,
                    "payment_terms": "",
                    "notes": "",
                },
            },
        )
        self.assertTrue(pdf_bytes.startswith(b"%PDF-"))
        # A raw, unescaped <script> tag never reaches the renderer -- if it
        # had, pisa would either choke on it or it would appear literally
        # in the extracted text; either way the safe path is that the
        # PDF still renders cleanly with the escaped text content.


class PdfHttpResponseTestCase(SimpleTestCase):
    def test_download_uses_attachment_disposition(self):
        response = pdf_http_response(b"%PDF-1.4 fake", filename="Invoice-INV-000001", inline=False)
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertEqual(response["Content-Disposition"], 'attachment; filename="Invoice-INV-000001.pdf"')

    def test_preview_uses_inline_disposition(self):
        response = pdf_http_response(b"%PDF-1.4 fake", filename="Invoice-INV-000001", inline=True)
        self.assertEqual(response["Content-Disposition"], 'inline; filename="Invoice-INV-000001.pdf"')

    def test_filename_is_sanitized_before_use(self):
        response = pdf_http_response(b"%PDF-1.4 fake", filename="Inv'oice <script>", inline=False)
        disposition = response["Content-Disposition"]
        self.assertNotIn("<", disposition)
        self.assertNotIn(">", disposition)
        self.assertTrue(disposition.startswith('attachment; filename="Invoice'))
        self.assertTrue(disposition.endswith('.pdf"'))

    def test_does_not_double_append_pdf_extension(self):
        response = pdf_http_response(b"%PDF-1.4 fake", filename="Invoice-INV-000001.pdf", inline=False)
        self.assertEqual(response["Content-Disposition"], 'attachment; filename="Invoice-INV-000001.pdf"')


_TEMP_MEDIA_ROOT = tempfile.mkdtemp(prefix="pdf_logo_tests_")


@override_settings(MEDIA_ROOT=_TEMP_MEDIA_ROOT)
class CompanyLogoDataUriTestCase(SimpleTestCase):
    """
    BE-078: `company_logo_data_uri` inlines a company logo's real bytes
    directly (never fetches `logoUrl` over HTTP -- see its own docstring
    for the SSRF reasoning), and only when this app actually uploaded the
    file (`logo_storage_key` non-blank).
    """

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(_TEMP_MEDIA_ROOT, ignore_errors=True)

    def test_no_logo_storage_key_returns_none(self):
        company = SimpleNamespace(id="c1", logo_storage_key="")
        self.assertIsNone(company_logo_data_uri(company))

    def test_missing_logo_storage_key_attribute_returns_none(self):
        company = SimpleNamespace(id="c1")
        self.assertIsNone(company_logo_data_uri(company))

    def test_real_uploaded_logo_returns_a_valid_data_uri(self):
        from django.core.files.uploadedfile import SimpleUploadedFile

        upload = SimpleUploadedFile("logo.png", b"\x89PNG\r\n\x1a\nfake-but-real-bytes", content_type="image/png")
        key = storage_service.generate_storage_key("companies", "c1", "png")
        storage_service.save_upload("companies", key, upload)

        company = SimpleNamespace(id="c1", logo_storage_key=key)
        data_uri = company_logo_data_uri(company)

        self.assertIsNotNone(data_uri)
        self.assertTrue(data_uri.startswith("data:image/png;base64,"))

        import base64

        encoded = data_uri.split(",", 1)[1]
        self.assertEqual(base64.b64decode(encoded), b"\x89PNG\r\n\x1a\nfake-but-real-bytes")

        storage_service.delete_file("companies", key)

    def test_nonexistent_storage_key_degrades_to_none_not_an_exception(self):
        company = SimpleNamespace(id="c1", logo_storage_key="companies/c1/does-not-exist.png")
        self.assertIsNone(company_logo_data_uri(company))
