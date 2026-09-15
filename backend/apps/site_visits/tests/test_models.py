import uuid
from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from apps.clients.models import Client
from apps.company.models import Company, CompanyStatus
from apps.leads.models import Lead
from apps.projects.models import Project
from apps.site_visits.models import SiteVisit


class SiteVisitModelTestCase(TestCase):
    """
    Unit test suite for SiteVisit domain model (BE-062).
    """

    def setUp(self):
        self.company = Company.objects.create(name="Test Company", status=CompanyStatus.ACTIVE)
        self.other_company = Company.objects.create(name="Other Company", status=CompanyStatus.ACTIVE)
        self.lead = Lead.objects.create(company=self.company, name="Jane Prospect")
        self.client_obj = Client.objects.create(company=self.company, name="Jane Client")
        self.project = Project.objects.create(company=self.company, client=self.client_obj, name="Kitchen Remodel")
        self.visit_date = timezone.now() + timedelta(days=3)

    def test_site_visit_creation_with_required_fields_only(self):
        visit = SiteVisit.objects.create(company=self.company, project=self.project, visit_date=self.visit_date)
        self.assertIsInstance(visit.id, uuid.UUID)
        self.assertEqual(visit.company, self.company)
        self.assertEqual(visit.project, self.project)
        self.assertIsNone(visit.lead)
        self.assertIsNotNone(visit.created_at)
        self.assertIsNotNone(visit.updated_at)
        self.assertIsNone(visit.deleted_at)
        self.assertFalse(visit.is_deleted)

    def test_site_visit_optional_field_defaults(self):
        visit = SiteVisit.objects.create(company=self.company, project=self.project, visit_date=self.visit_date)
        self.assertEqual(visit.address, "")
        self.assertEqual(visit.measurements, "")
        self.assertEqual(visit.requirements, "")
        self.assertEqual(visit.photo_urls, [])
        self.assertEqual(visit.video_urls, [])
        self.assertEqual(visit.notes, "")
        self.assertIsNone(visit.budget)
        self.assertEqual(visit.site_conditions, "")
        self.assertEqual(visit.follow_up_actions, "")
        self.assertIsNone(visit.report_submitted_at)
        self.assertIsNone(visit.assigned_to)
        self.assertIsNone(visit.client)

    def test_is_completed_property(self):
        visit = SiteVisit.objects.create(company=self.company, project=self.project, visit_date=self.visit_date)
        self.assertFalse(visit.is_completed)

        visit.report_submitted_at = timezone.now()
        visit.save()
        self.assertTrue(visit.is_completed)

    def test_site_visit_can_be_scheduled_against_lead_only(self):
        visit = SiteVisit.objects.create(company=self.company, lead=self.lead, visit_date=self.visit_date)
        self.assertEqual(visit.lead, self.lead)
        self.assertIsNone(visit.project)

    def test_site_visit_can_be_scheduled_against_both_lead_and_project(self):
        visit = SiteVisit.objects.create(
            company=self.company, lead=self.lead, project=self.project, visit_date=self.visit_date
        )
        self.assertEqual(visit.lead, self.lead)
        self.assertEqual(visit.project, self.project)

    def test_site_visit_tenant_isolation_via_company_fk(self):
        SiteVisit.objects.create(company=self.company, project=self.project, visit_date=self.visit_date)
        other_project = Project.objects.create(
            company=self.other_company,
            client=Client.objects.create(company=self.other_company, name="Other Client"),
            name="Other Project",
        )
        SiteVisit.objects.create(company=self.other_company, project=other_project, visit_date=self.visit_date)

        company_visits = SiteVisit.objects.filter(company=self.company)
        self.assertEqual(company_visits.count(), 1)

    def test_site_visit_soft_delete_lifecycle(self):
        visit = SiteVisit.objects.create(company=self.company, project=self.project, visit_date=self.visit_date)
        visit_id = visit.id

        visit.delete()
        self.assertTrue(visit.is_deleted)
        self.assertIsNotNone(visit.deleted_at)

        self.assertFalse(SiteVisit.objects.filter(id=visit_id).exists())
        self.assertTrue(SiteVisit.all_objects.filter(id=visit_id).exists())
        self.assertTrue(SiteVisit.deleted_objects.filter(id=visit_id).exists())

        visit.restore()
        self.assertFalse(visit.is_deleted)
        self.assertTrue(SiteVisit.objects.filter(id=visit_id).exists())

    def test_site_visit_cascade_delete_with_company(self):
        # Scheduled against the lead only (not the project) — Project.client
        # is on_delete=PROTECT, so a company with an existing Project can
        # never be hard-deleted regardless of this test's own concerns;
        # using the lead-only relation keeps this test scoped to SiteVisit's
        # own CASCADE behavior on its `company` FK.
        visit = SiteVisit.objects.create(company=self.company, lead=self.lead, visit_date=self.visit_date)
        visit_id = visit.id
        self.project.delete(hard=True)
        self.client_obj.delete(hard=True)
        self.company.delete(hard=True)
        self.assertFalse(SiteVisit.all_objects.filter(id=visit_id).exists())

    def test_site_visit_requires_company(self):
        with self.assertRaises(Exception):
            SiteVisit.objects.create(project=self.project, visit_date=self.visit_date)

    def test_lead_set_null_on_lead_delete(self):
        visit = SiteVisit.objects.create(company=self.company, lead=self.lead, visit_date=self.visit_date)
        self.lead.delete(hard=True)
        visit.refresh_from_db()
        self.assertIsNone(visit.lead)

    def test_project_set_null_on_project_delete(self):
        visit = SiteVisit.objects.create(company=self.company, project=self.project, visit_date=self.visit_date)
        self.project.delete(hard=True)
        visit.refresh_from_db()
        self.assertIsNone(visit.project)

    def test_client_set_null_on_client_delete(self):
        standalone_client = Client.objects.create(company=self.company, name="Standalone Client")
        visit = SiteVisit.objects.create(
            company=self.company, lead=self.lead, client=standalone_client, visit_date=self.visit_date
        )
        standalone_client.delete(hard=True)
        visit.refresh_from_db()
        self.assertIsNone(visit.client)
