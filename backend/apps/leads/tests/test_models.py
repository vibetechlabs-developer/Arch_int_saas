import uuid
from django.test import TestCase

from apps.leads.models import Lead, LeadStatus
from apps.company.models import Company, CompanyStatus


class LeadModelTestCase(TestCase):
    """
    Unit test suite for Lead domain model (BE-061).
    """

    def setUp(self):
        self.company = Company.objects.create(name="Test Company", status=CompanyStatus.ACTIVE)
        self.other_company = Company.objects.create(name="Other Company", status=CompanyStatus.ACTIVE)

    def test_lead_creation_with_required_field_only(self):
        lead = Lead.objects.create(company=self.company, name="Jane Prospect")
        self.assertIsInstance(lead.id, uuid.UUID)
        self.assertEqual(lead.name, "Jane Prospect")
        self.assertEqual(lead.company, self.company)
        self.assertEqual(lead.status, LeadStatus.NEW)
        self.assertIsNotNone(lead.created_at)
        self.assertIsNotNone(lead.updated_at)
        self.assertIsNone(lead.deleted_at)
        self.assertFalse(lead.is_deleted)

    def test_lead_optional_field_defaults(self):
        lead = Lead.objects.create(company=self.company, name="Jane Prospect")
        self.assertEqual(lead.company_name, "")
        self.assertEqual(lead.email, "")
        self.assertEqual(lead.mobile, "")
        self.assertEqual(lead.source, "")
        self.assertEqual(lead.loss_reason, "")
        self.assertIsNone(lead.follow_up_reminder_at)
        self.assertEqual(lead.notes, "")
        self.assertIsNone(lead.assigned_to)
        self.assertIsNone(lead.converted_client)
        self.assertIsNone(lead.converted_project)

    def test_lead_creation_with_all_fields(self):
        lead = Lead.objects.create(
            company=self.company,
            name="Jane Prospect",
            company_name="Prospect Interiors",
            email="jane@example.com",
            mobile="+91-9999999999",
            source="referral",
            notes="Interested in a 3BHK renovation.",
        )
        lead.refresh_from_db()
        self.assertEqual(lead.company_name, "Prospect Interiors")
        self.assertEqual(lead.email, "jane@example.com")
        self.assertEqual(lead.mobile, "+91-9999999999")
        self.assertEqual(lead.source, "referral")
        self.assertEqual(lead.notes, "Interested in a 3BHK renovation.")

    def test_lead_str_representation(self):
        lead = Lead.objects.create(company=self.company, name="Jane Prospect")
        self.assertEqual(str(lead), f"Jane Prospect ({self.company.name})")

    def test_lead_no_uniqueness_constraint_on_name(self):
        lead1 = Lead.objects.create(company=self.company, name="Jane Prospect")
        lead2 = Lead.objects.create(company=self.company, name="Jane Prospect")
        self.assertNotEqual(lead1.id, lead2.id)
        self.assertEqual(
            Lead.objects.filter(company=self.company, name="Jane Prospect").count(), 2
        )

    def test_lead_tenant_isolation_via_company_fk(self):
        Lead.objects.create(company=self.company, name="Company A Lead")
        Lead.objects.create(company=self.other_company, name="Company B Lead")

        company_leads = Lead.objects.filter(company=self.company)
        self.assertEqual(company_leads.count(), 1)
        self.assertEqual(company_leads.first().name, "Company A Lead")

    def test_lead_soft_delete_lifecycle(self):
        lead = Lead.objects.create(company=self.company, name="Jane Prospect")
        lead_id = lead.id

        lead.delete()
        self.assertTrue(lead.is_deleted)
        self.assertIsNotNone(lead.deleted_at)

        self.assertFalse(Lead.objects.filter(id=lead_id).exists())
        self.assertTrue(Lead.all_objects.filter(id=lead_id).exists())
        self.assertTrue(Lead.deleted_objects.filter(id=lead_id).exists())

        lead.restore()
        self.assertFalse(lead.is_deleted)
        self.assertIsNone(lead.deleted_at)
        self.assertTrue(Lead.objects.filter(id=lead_id).exists())

    def test_lead_cascade_delete_with_company(self):
        lead = Lead.objects.create(company=self.company, name="Jane Prospect")
        lead_id = lead.id
        self.company.delete(hard=True)
        self.assertFalse(Lead.all_objects.filter(id=lead_id).exists())

    def test_lead_requires_company(self):
        with self.assertRaises(Exception):
            Lead.objects.create(name="No Company Lead")

    def test_assigned_to_set_null_on_user_delete(self):
        from django.contrib.auth import get_user_model

        User = get_user_model()
        user = User.objects.create_user(
            email="sales@example.com", name="Sales Rep", password="StrongPassword123!"
        )
        lead = Lead.objects.create(company=self.company, name="Jane Prospect", assigned_to=user)
        user.delete(hard=True)
        lead.refresh_from_db()
        self.assertIsNone(lead.assigned_to)

    def test_converted_client_set_null_on_client_delete(self):
        from apps.clients.models import Client

        client = Client.objects.create(company=self.company, name="Jane Prospect")
        lead = Lead.objects.create(
            company=self.company, name="Jane Prospect", status=LeadStatus.WON, converted_client=client
        )
        client.delete(hard=True)
        lead.refresh_from_db()
        self.assertIsNone(lead.converted_client)


class GetAllowedNextStatusesTestCase(TestCase):
    """
    Unit tests for the pure BE-061 transition graph function, mirroring
    apps.projects.tests.test_workflow.GetAllowedNextStatusesTestCase.
    """

    def test_terminal_statuses_have_no_transitions(self):
        from apps.leads.models import get_allowed_next_statuses

        self.assertEqual(get_allowed_next_statuses(LeadStatus.WON), set())
        self.assertEqual(get_allowed_next_statuses(LeadStatus.LOST), set())

    def test_new_can_move_to_qualified_or_lost(self):
        from apps.leads.models import get_allowed_next_statuses

        allowed = get_allowed_next_statuses(LeadStatus.NEW)
        self.assertEqual(allowed, {LeadStatus.QUALIFIED, LeadStatus.LOST})

    def test_no_skipping_ahead(self):
        from apps.leads.models import get_allowed_next_statuses

        allowed = get_allowed_next_statuses(LeadStatus.NEW)
        self.assertNotIn(LeadStatus.SITE_VISIT_SCHEDULED, allowed)

    def test_no_moving_backward(self):
        from apps.leads.models import get_allowed_next_statuses

        allowed = get_allowed_next_statuses(LeadStatus.SITE_VISIT_SCHEDULED)
        self.assertNotIn(LeadStatus.QUALIFIED, allowed)
        self.assertNotIn(LeadStatus.NEW, allowed)

    def test_site_visit_scheduled_cannot_advance_further_in_main_chain(self):
        """SITE_VISIT_SCHEDULED is the last MAIN_CHAIN_STATUSES entry — only LOST is reachable, never WON directly."""
        from apps.leads.models import get_allowed_next_statuses

        allowed = get_allowed_next_statuses(LeadStatus.SITE_VISIT_SCHEDULED)
        self.assertEqual(allowed, {LeadStatus.LOST})
        self.assertNotIn(LeadStatus.WON, allowed)

    def test_won_is_never_reachable_via_this_function_from_any_status(self):
        from apps.leads.models import MAIN_CHAIN_STATUSES, get_allowed_next_statuses

        for chain_status in MAIN_CHAIN_STATUSES:
            self.assertNotIn(LeadStatus.WON, get_allowed_next_statuses(chain_status))

    def test_every_main_chain_status_can_reach_lost(self):
        from apps.leads.models import MAIN_CHAIN_STATUSES, get_allowed_next_statuses

        for chain_status in MAIN_CHAIN_STATUSES:
            self.assertIn(LeadStatus.LOST, get_allowed_next_statuses(chain_status))
