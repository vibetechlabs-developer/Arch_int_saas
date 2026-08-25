from django.test import TestCase

from apps.company.models import Company, CompanyStatus
from apps.company.serializers import CompanySerializer


class CompanySerializerTestCase(TestCase):
    """
    Unit tests for CompanySerializer (BE-010).
    """

    def setUp(self):
        self.company = Company.objects.create(
            name="Studio Forma",
            status=CompanyStatus.ACTIVE,
            currency="INR",
            gst_number="29ABCDE1234F1Z5",
            settings={"numbering": {"invoicePrefix": "SF-INV-"}},
        )

    def test_company_serializer_output_fields(self):
        """
        Verify that CompanySerializer produces camelCase field names matching API standards.
        """
        serializer = CompanySerializer(self.company)
        data = serializer.data

        expected_fields = {
            "id",
            "name",
            "status",
            "currency",
            "gstNumber",
            "settings",
            "createdAt",
            "updatedAt",
        }
        self.assertEqual(set(data.keys()), expected_fields)
        self.assertEqual(str(data["id"]), str(self.company.id))
        self.assertEqual(data["name"], "Studio Forma")
        self.assertEqual(data["status"], "active")
        self.assertEqual(data["currency"], "INR")
        self.assertEqual(data["gstNumber"], "29ABCDE1234F1Z5")
        self.assertEqual(data["settings"], {"numbering": {"invoicePrefix": "SF-INV-"}})

    def test_company_serializer_with_null_gst(self):
        """
        Verify serializer handles null gst_number cleanly.
        """
        company_no_gst = Company.objects.create(name="No GST Enterprise")
        serializer = CompanySerializer(company_no_gst)
        data = serializer.data

        self.assertIsNone(data["gstNumber"])
        self.assertEqual(data["name"], "No GST Enterprise")
        self.assertEqual(data["status"], "trial")
