import uuid
from django.test import TestCase
from django.utils import timezone

from apps.company.models import Company, CompanyStatus, get_default_company_settings


class CompanyModelTestCase(TestCase):
    """
    Unit tests for the Company model (BE-010).
    """

    def setUp(self):
        self.company = Company.objects.create(
            name="Acme Interiors Pvt Ltd",
        )

    def test_company_creation_defaults(self):
        """
        Verify Company creation with default values.
        """
        self.assertIsInstance(self.company.id, uuid.UUID)
        self.assertEqual(self.company.name, "Acme Interiors Pvt Ltd")
        self.assertEqual(self.company.status, CompanyStatus.TRIAL)
        self.assertEqual(self.company.currency, "INR")
        self.assertIsNone(self.company.gst_number)
        self.assertEqual(self.company.settings, get_default_company_settings())
        self.assertIsNotNone(self.company.created_at)
        self.assertIsNotNone(self.company.updated_at)
        self.assertIsNone(self.company.deleted_at)
        self.assertFalse(self.company.is_deleted)

    def test_company_str_representation(self):
        """
        Verify string representation format: 'name (status)'.
        """
        self.assertEqual(str(self.company), "Acme Interiors Pvt Ltd (trial)")
        self.company.status = CompanyStatus.ACTIVE
        self.company.save()
        self.assertEqual(str(self.company), "Acme Interiors Pvt Ltd (active)")

    def test_company_status_choices(self):
        """
        Verify that status can be set to all defined CompanyStatus choices.
        """
        for status_val in [CompanyStatus.TRIAL, CompanyStatus.ACTIVE, CompanyStatus.SUSPENDED]:
            self.company.status = status_val
            self.company.save()
            self.company.refresh_from_db()
            self.assertEqual(self.company.status, status_val)

    def test_company_custom_fields(self):
        """
        Verify Company creation with custom fields (currency, GSTIN, settings).
        """
        custom_settings = {
            "numbering": {"invoicePrefix": "INV-", "quotePrefix": "QUO-"},
            "paymentTerms": {"defaultDays": 30},
            "notificationPrefs": {"emailOnInvoice": True},
        }
        company = Company.objects.create(
            name="Design Studio LLC",
            status=CompanyStatus.ACTIVE,
            currency="USD",
            gst_number="27ABCDE1234F1Z5",
            settings=custom_settings,
        )

        self.assertEqual(company.currency, "USD")
        self.assertEqual(company.gst_number, "27ABCDE1234F1Z5")
        self.assertEqual(company.settings["numbering"]["invoicePrefix"], "INV-")
        self.assertEqual(company.settings["paymentTerms"]["defaultDays"], 30)

    def test_company_uuid_uniqueness(self):
        """
        Verify that distinct companies receive distinct UUID primary keys.
        """
        company2 = Company.objects.create(name="Second Studio")
        self.assertNotEqual(self.company.id, company2.id)

    def test_company_soft_delete_lifecycle(self):
        """
        Verify soft delete, restore, and manager behavior for Company model.
        """
        company_id = self.company.id

        # 1. Soft delete
        self.company.delete()
        self.assertTrue(self.company.is_deleted)
        self.assertIsNotNone(self.company.deleted_at)

        # 2. Excluded from default manager
        self.assertFalse(Company.objects.filter(id=company_id).exists())

        # 3. Present in all_objects and deleted_objects
        self.assertTrue(Company.all_objects.filter(id=company_id).exists())
        self.assertTrue(Company.deleted_objects.filter(id=company_id).exists())

        # 4. Restore
        self.company.restore()
        self.assertFalse(self.company.is_deleted)
        self.assertIsNone(self.company.deleted_at)
        self.assertTrue(Company.objects.filter(id=company_id).exists())
        self.assertFalse(Company.deleted_objects.filter(id=company_id).exists())

        # 5. Hard delete
        self.company.hard_delete()
        self.assertFalse(Company.all_objects.filter(id=company_id).exists())

    def test_company_bulk_soft_delete_and_restore(self):
        """
        Verify bulk soft delete and restore via custom QuerySet methods.
        """
        c1 = Company.objects.create(name="Bulk Company 1")
        c2 = Company.objects.create(name="Bulk Company 2")

        Company.objects.filter(id__in=[c1.id, c2.id]).delete()
        self.assertEqual(Company.objects.filter(id__in=[c1.id, c2.id]).count(), 0)
        self.assertEqual(Company.deleted_objects.filter(id__in=[c1.id, c2.id]).count(), 2)

        Company.all_objects.filter(id__in=[c1.id, c2.id]).restore()
        self.assertEqual(Company.objects.filter(id__in=[c1.id, c2.id]).count(), 2)
        self.assertEqual(Company.deleted_objects.filter(id__in=[c1.id, c2.id]).count(), 0)
