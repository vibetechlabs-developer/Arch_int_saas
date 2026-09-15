import uuid
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework import exceptions as drf_exceptions

from apps.audit.models import AuditLog
from apps.clients.models import Client
from apps.common.exceptions import ConflictError
from apps.company.models import Company, CompanyStatus
from apps.leads.models import Lead
from apps.leads.services import LeadService
from apps.projects.models import Project
from apps.site_visits.models import SiteVisit
from apps.site_visits.services import SiteVisitService
from apps.users.models import CompanyMembership, CompanyMembershipStatus

User = get_user_model()


class SiteVisitServiceTestCase(TestCase):
    """
    Unit test suite for SiteVisitService business logic (BE-062), mirroring
    apps.leads.tests.test_services.LeadServiceTestCase's structure.
    """

    def setUp(self):
        self.company1 = Company.objects.create(name="Alpha Corp", status=CompanyStatus.ACTIVE)
        self.company2 = Company.objects.create(name="Beta Corp", status=CompanyStatus.ACTIVE)

        self.sales_user = User.objects.create_user(
            email="sales@alpha.com", name="Sales Rep", password="StrongPassword123!"
        )
        CompanyMembership.objects.create(
            company=self.company1, user=self.sales_user, status=CompanyMembershipStatus.ACTIVE
        )

        self.lead = LeadService.create_lead(company_id=self.company1.id, name="Jane Prospect")
        self.client_obj = Client.objects.create(company=self.company1, name="Existing Client")
        self.project = Project.objects.create(company=self.company1, client=self.client_obj, name="Kitchen Remodel")

        self.lead_c2 = Lead.objects.create(company=self.company2, name="Other Lead")

        self.visit_date = timezone.now() + timedelta(days=2)

    # --- create ------------------------------------------------------

    def test_create_site_visit_against_project_resolves_client(self):
        visit = SiteVisitService.create_site_visit(
            company_id=self.company1.id, project_id=self.project.id, visit_date=self.visit_date
        )
        self.assertEqual(visit.project_id, self.project.id)
        self.assertEqual(visit.client_id, self.client_obj.id)

    def test_create_site_visit_against_lead_only_no_client_yet(self):
        visit = SiteVisitService.create_site_visit(
            company_id=self.company1.id, lead_id=self.lead.id, visit_date=self.visit_date
        )
        self.assertEqual(visit.lead_id, self.lead.id)
        self.assertIsNone(visit.client_id)

    def test_create_site_visit_against_converted_lead_resolves_client(self):
        converted = LeadService.convert_lead(self.lead.id)
        visit = SiteVisitService.create_site_visit(
            company_id=self.company1.id, lead_id=self.lead.id, visit_date=self.visit_date
        )
        self.assertEqual(visit.client_id, converted.converted_client_id)

    def test_create_site_visit_neither_lead_nor_project_raises_value_error(self):
        with self.assertRaises(ValueError):
            SiteVisitService.create_site_visit(company_id=self.company1.id, visit_date=self.visit_date)

    def test_create_site_visit_nonexistent_company_raises_not_found(self):
        with self.assertRaises(drf_exceptions.NotFound):
            SiteVisitService.create_site_visit(
                company_id=uuid.uuid4(), project_id=self.project.id, visit_date=self.visit_date
            )

    def test_create_site_visit_cross_tenant_project_raises_not_found(self):
        other_project = Project.objects.create(
            company=self.company2,
            client=Client.objects.create(company=self.company2, name="Other Co Client"),
            name="Other Project",
        )
        with self.assertRaises(drf_exceptions.NotFound):
            SiteVisitService.create_site_visit(
                company_id=self.company1.id, project_id=other_project.id, visit_date=self.visit_date
            )

    def test_create_site_visit_cross_tenant_lead_raises_not_found(self):
        with self.assertRaises(drf_exceptions.NotFound):
            SiteVisitService.create_site_visit(
                company_id=self.company1.id, lead_id=self.lead_c2.id, visit_date=self.visit_date
            )

    def test_create_site_visit_with_valid_assignee(self):
        visit = SiteVisitService.create_site_visit(
            company_id=self.company1.id,
            project_id=self.project.id,
            visit_date=self.visit_date,
            assigned_to_id=self.sales_user.id,
        )
        self.assertEqual(visit.assigned_to_id, self.sales_user.id)

    def test_create_site_visit_with_assignee_not_a_member_raises_validation_error(self):
        outsider = User.objects.create_user(
            email="outsider@example.com", name="Outsider", password="StrongPassword123!"
        )
        with self.assertRaises(drf_exceptions.ValidationError):
            SiteVisitService.create_site_visit(
                company_id=self.company1.id,
                project_id=self.project.id,
                visit_date=self.visit_date,
                assigned_to_id=outsider.id,
            )

    def test_create_site_visit_writes_audit_log_entry(self):
        visit = SiteVisitService.create_site_visit(
            company_id=self.company1.id, project_id=self.project.id, visit_date=self.visit_date
        )
        entry = AuditLog.objects.get(entity_type="site_visit", entity_id=visit.id, action="create")
        self.assertEqual(entry.company_id, self.company1.id)
        self.assertIsNone(entry.before_state)
        self.assertEqual(entry.after_state["project_id"], str(self.project.id))

    # --- get/list ------------------------------------------------------

    def test_get_site_visit_by_id_success(self):
        visit = SiteVisitService.create_site_visit(
            company_id=self.company1.id, project_id=self.project.id, visit_date=self.visit_date
        )
        fetched = SiteVisitService.get_site_visit_by_id(visit.id)
        self.assertEqual(fetched.id, visit.id)

    def test_get_site_visit_by_id_cross_tenant_raises_not_found(self):
        visit = SiteVisitService.create_site_visit(
            company_id=self.company1.id, project_id=self.project.id, visit_date=self.visit_date
        )
        with self.assertRaises(drf_exceptions.NotFound):
            SiteVisitService.get_site_visit_by_id(visit.id, company_id=self.company2.id)

    def test_list_site_visits_filtering_by_company(self):
        SiteVisitService.create_site_visit(
            company_id=self.company1.id, project_id=self.project.id, visit_date=self.visit_date
        )
        other_project = Project.objects.create(
            company=self.company2,
            client=Client.objects.create(company=self.company2, name="Other Co Client 2"),
            name="Other Project 2",
        )
        SiteVisitService.create_site_visit(
            company_id=self.company2.id, project_id=other_project.id, visit_date=self.visit_date
        )
        results = SiteVisitService.list_site_visits(company_id=self.company1.id)
        self.assertEqual(results.count(), 1)

    def test_list_site_visits_filtering_by_lead(self):
        SiteVisitService.create_site_visit(company_id=self.company1.id, lead_id=self.lead.id, visit_date=self.visit_date)
        SiteVisitService.create_site_visit(company_id=self.company1.id, project_id=self.project.id, visit_date=self.visit_date)
        results = SiteVisitService.list_site_visits(company_id=self.company1.id, lead_id=self.lead.id)
        self.assertEqual(results.count(), 1)

    def test_list_site_visits_for_viewer_platform_admin_sees_all(self):
        SiteVisitService.create_site_visit(company_id=self.company1.id, project_id=self.project.id, visit_date=self.visit_date)
        other_project = Project.objects.create(
            company=self.company2,
            client=Client.objects.create(company=self.company2, name="Other Co Client 3"),
            name="Other Project 3",
        )
        SiteVisitService.create_site_visit(company_id=self.company2.id, project_id=other_project.id, visit_date=self.visit_date)

        queryset = SiteVisitService.list_site_visits_for_viewer(
            is_platform_admin=True, resolved_company_id=None, admin_company_id_param=None
        )
        self.assertEqual(queryset.count(), 2)

    # --- update ------------------------------------------------------

    def test_update_site_visit_success(self):
        visit = SiteVisitService.create_site_visit(
            company_id=self.company1.id, project_id=self.project.id, visit_date=self.visit_date
        )
        updated = SiteVisitService.update_site_visit(
            site_visit_id=visit.id, validated_data={"address": "221B Baker St", "budget": "5000.00"}
        )
        self.assertEqual(updated.address, "221B Baker St")
        self.assertEqual(str(updated.budget), "5000.00")

    def test_update_site_visit_cross_tenant_scoping_raises_not_found(self):
        visit = SiteVisitService.create_site_visit(
            company_id=self.company1.id, project_id=self.project.id, visit_date=self.visit_date
        )
        with self.assertRaises(drf_exceptions.NotFound):
            SiteVisitService.update_site_visit(
                site_visit_id=visit.id, validated_data={"address": "Hacked"}, company_id=self.company2.id
            )

    def test_update_site_visit_clear_assignee_with_null(self):
        visit = SiteVisitService.create_site_visit(
            company_id=self.company1.id,
            project_id=self.project.id,
            visit_date=self.visit_date,
            assigned_to_id=self.sales_user.id,
        )
        updated = SiteVisitService.update_site_visit(site_visit_id=visit.id, validated_data={"assigned_to_id": None})
        self.assertIsNone(updated.assigned_to_id)

    def test_update_site_visit_writes_audit_log_entry(self):
        visit = SiteVisitService.create_site_visit(
            company_id=self.company1.id, project_id=self.project.id, visit_date=self.visit_date
        )
        SiteVisitService.update_site_visit(site_visit_id=visit.id, validated_data={"address": "New Address"})
        entry = AuditLog.objects.filter(
            entity_type="site_visit", entity_id=visit.id, action="update"
        ).latest("created_at")
        self.assertEqual(entry.after_state["address"], "New Address")

    # --- delete ------------------------------------------------------

    def test_soft_delete_site_visit(self):
        visit = SiteVisitService.create_site_visit(
            company_id=self.company1.id, project_id=self.project.id, visit_date=self.visit_date
        )
        SiteVisitService.soft_delete_site_visit(visit.id)
        with self.assertRaises(drf_exceptions.NotFound):
            SiteVisitService.get_site_visit_by_id(visit.id)
        self.assertTrue(SiteVisit.all_objects.filter(id=visit.id).exists())

    # --- submit_report ------------------------------------------------------

    def test_submit_report_marks_completed(self):
        visit = SiteVisitService.create_site_visit(
            company_id=self.company1.id, project_id=self.project.id, visit_date=self.visit_date
        )
        updated = SiteVisitService.submit_report(visit.id)
        self.assertTrue(updated.is_completed)
        self.assertIsNotNone(updated.report_submitted_at)

    def test_submit_report_is_idempotent(self):
        visit = SiteVisitService.create_site_visit(
            company_id=self.company1.id, project_id=self.project.id, visit_date=self.visit_date
        )
        first = SiteVisitService.submit_report(visit.id)
        second = SiteVisitService.submit_report(visit.id)
        self.assertEqual(first.report_submitted_at, second.report_submitted_at)

    def test_submit_report_with_create_project_when_client_resolved_from_converted_lead(self):
        converted = LeadService.convert_lead(self.lead.id)
        visit = SiteVisitService.create_site_visit(
            company_id=self.company1.id, lead_id=self.lead.id, visit_date=self.visit_date
        )
        updated = SiteVisitService.submit_report(visit.id, create_project=True, project_name="New Project From Visit")
        self.assertIsNotNone(updated.project_id)
        project = Project.objects.get(id=updated.project_id)
        self.assertEqual(project.name, "New Project From Visit")

    def test_submit_report_re_resolves_client_when_lead_converted_after_visit_was_scheduled(self):
        """
        Realistic ordering: schedule the visit against the lead FIRST
        (no client exists yet), convert the lead LATER, then submit the
        report -- the visit's `client` must not stay permanently null
        just because it was null at creation time (caught via live HTTP
        verification, not by the create-then-convert ordering the sibling
        test above uses).
        """
        visit = SiteVisitService.create_site_visit(
            company_id=self.company1.id, lead_id=self.lead.id, visit_date=self.visit_date
        )
        self.assertIsNone(visit.client_id)

        converted = LeadService.convert_lead(self.lead.id)
        updated = SiteVisitService.submit_report(visit.id, create_project=True, project_name="Post-Conversion Project")

        self.assertEqual(updated.client_id, converted.converted_client_id)
        self.assertIsNotNone(updated.project_id)

    def test_submit_report_create_project_syncs_lead_converted_project(self):
        LeadService.convert_lead(self.lead.id)
        visit = SiteVisitService.create_site_visit(
            company_id=self.company1.id, lead_id=self.lead.id, visit_date=self.visit_date
        )
        updated = SiteVisitService.submit_report(visit.id, create_project=True)
        self.lead.refresh_from_db()
        self.assertEqual(self.lead.converted_project_id, updated.project_id)

    def test_submit_report_create_project_without_resolved_client_raises_conflict(self):
        visit = SiteVisitService.create_site_visit(
            company_id=self.company1.id, lead_id=self.lead.id, visit_date=self.visit_date
        )
        with self.assertRaises(ConflictError):
            SiteVisitService.submit_report(visit.id, create_project=True)

    def test_submit_report_already_has_project_does_not_create_duplicate(self):
        visit = SiteVisitService.create_site_visit(
            company_id=self.company1.id, project_id=self.project.id, visit_date=self.visit_date
        )
        project_count_before = Project.objects.filter(company=self.company1).count()
        updated = SiteVisitService.submit_report(visit.id, create_project=True)
        project_count_after = Project.objects.filter(company=self.company1).count()
        self.assertEqual(updated.project_id, self.project.id)
        self.assertEqual(project_count_before, project_count_after)

    def test_submit_report_cross_tenant_raises_not_found(self):
        visit = SiteVisitService.create_site_visit(
            company_id=self.company1.id, project_id=self.project.id, visit_date=self.visit_date
        )
        with self.assertRaises(drf_exceptions.NotFound):
            SiteVisitService.submit_report(visit.id, company_id=self.company2.id)

    def test_submit_report_writes_single_audit_entry(self):
        visit = SiteVisitService.create_site_visit(
            company_id=self.company1.id, project_id=self.project.id, visit_date=self.visit_date
        )
        before_count = AuditLog.objects.filter(entity_type="site_visit", entity_id=visit.id).count()
        SiteVisitService.submit_report(visit.id)
        after_count = AuditLog.objects.filter(entity_type="site_visit", entity_id=visit.id).count()
        self.assertEqual(after_count, before_count + 1)

    def test_submit_report_idempotent_does_not_write_second_audit_entry(self):
        visit = SiteVisitService.create_site_visit(
            company_id=self.company1.id, project_id=self.project.id, visit_date=self.visit_date
        )
        SiteVisitService.submit_report(visit.id)
        count_after_first = AuditLog.objects.filter(entity_type="site_visit", entity_id=visit.id).count()
        SiteVisitService.submit_report(visit.id)
        count_after_second = AuditLog.objects.filter(entity_type="site_visit", entity_id=visit.id).count()
        self.assertEqual(count_after_first, count_after_second)
