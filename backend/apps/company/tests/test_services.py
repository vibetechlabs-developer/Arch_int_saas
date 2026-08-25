import uuid
from django.test import TestCase
from rest_framework.exceptions import NotFound

from apps.company.models import Company, CompanyStatus
from apps.company.services import CompanyService


class CompanyServiceTestCase(TestCase):
    """
    Unit tests for CompanyService business logic (BE-011).
    """

    def setUp(self):
        self.company = CompanyService.create_company(
            name="Apex Interiors",
            currency="INR",
            gst_number="27AAAAA0000A1Z5",
            status="active",
            settings={"paymentTerms": {"defaultDays": 15}},
        )

    def test_create_company_with_defaults(self):
        """
        Verify company creation with default parameters.
        """
        c = CompanyService.create_company(name="Standard Design Studio")
        self.assertIsInstance(c.id, uuid.UUID)
        self.assertEqual(c.name, "Standard Design Studio")
        self.assertEqual(c.status, "trial")
        self.assertEqual(c.currency, "INR")
        self.assertIsNone(c.gst_number)
        self.assertIn("numbering", c.settings)

    def test_get_company_by_id_success(self):
        """
        Verify retrieving existing company by ID.
        """
        fetched = CompanyService.get_company_by_id(self.company.id)
        self.assertEqual(fetched.id, self.company.id)
        self.assertEqual(fetched.name, "Apex Interiors")

    def test_get_company_by_id_nonexistent_raises_not_found(self):
        """
        Verify that querying non-existent company raises NotFound (404).
        """
        random_id = uuid.uuid4()
        with self.assertRaises(NotFound):
            CompanyService.get_company_by_id(random_id)

    def test_list_companies_filtering_and_search(self):
        """
        Verify listing companies with status filters and search terms.
        """
        CompanyService.create_company(name="Beta Design", status="trial")
        CompanyService.create_company(name="Gamma Architecture", status="suspended")

        active_list = CompanyService.list_companies(status="active")
        self.assertEqual(active_list.count(), 1)
        self.assertEqual(active_list.first().name, "Apex Interiors")

        trial_list = CompanyService.list_companies(status="trial")
        self.assertEqual(trial_list.count(), 1)
        self.assertEqual(trial_list.first().name, "Beta Design")

        search_results = CompanyService.list_companies(search="Gamma")
        self.assertEqual(search_results.count(), 1)
        self.assertEqual(search_results.first().name, "Gamma Architecture")

    def test_update_company_by_member_cannot_change_status(self):
        """
        Verify that regular updates cannot alter tenant status.
        """
        updated = CompanyService.update_company(
            company_id=self.company.id,
            validated_data={"name": "Apex Global Interiors", "status": "suspended"},
            is_platform_admin=False,
        )
        self.assertEqual(updated.name, "Apex Global Interiors")
        # Status remains active because is_platform_admin is False
        self.assertEqual(updated.status, "active")

    def test_update_company_by_platform_admin_can_change_status(self):
        """
        Verify that platform admin can alter tenant status.
        """
        updated = CompanyService.update_company(
            company_id=self.company.id,
            validated_data={"status": "suspended"},
            is_platform_admin=True,
        )
        self.assertEqual(updated.status, "suspended")

    def test_update_company_settings_merge_is_shallow(self):
        """
        BE-018 (Decision 2 — documented, not redesigned): CompanyService's
        settings update is a top-level SHALLOW merge (apps/company/
        validators.py::build_update_fields), not a deep/recursive merge.

        Updating one top-level settings key:
        - leaves sibling top-level keys (e.g. "numbering") completely
          untouched, and
        - REPLACES the targeted key's entire value rather than merging into
          it — so supplying {"paymentTerms": {"lateFeePercent": 2}} drops
          any other keys ("defaultDays") that were previously inside
          paymentTerms.

        This is current, accepted behavior — this test locks it in as a
        regression guard, it is not asserting this is the "correct" design.
        """
        company = CompanyService.create_company(
            name="Merge Behavior Co",
            settings={
                "numbering": {"invoicePrefix": "MBC-"},
                "paymentTerms": {"defaultDays": 15, "lateFeePercent": 0},
            },
        )

        updated = CompanyService.update_company(
            company_id=company.id,
            validated_data={"settings": {"paymentTerms": {"lateFeePercent": 2}}},
            is_platform_admin=False,
        )

        # Sibling top-level key is untouched.
        self.assertEqual(updated.settings["numbering"], {"invoicePrefix": "MBC-"})
        # Targeted key is replaced wholesale, not deep-merged: "defaultDays"
        # is gone, only the newly-supplied "lateFeePercent" remains.
        self.assertEqual(updated.settings["paymentTerms"], {"lateFeePercent": 2})
        self.assertNotIn("defaultDays", updated.settings["paymentTerms"])

    def test_soft_delete_company(self):
        """
        Verify that soft delete marks deleted_at and hides company from get_company_by_id.
        """
        c_id = self.company.id
        CompanyService.soft_delete_company(c_id)

        with self.assertRaises(NotFound):
            CompanyService.get_company_by_id(c_id)

        # Still accessible in all_objects
        self.assertTrue(Company.all_objects.filter(id=c_id).exists())
