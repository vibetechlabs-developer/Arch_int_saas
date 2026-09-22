import uuid
from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import exceptions as drf_exceptions

from apps.audit.models import AuditLog
from apps.clients.models import Client
from apps.common.exceptions import ConflictError
from apps.company.models import Company, CompanyStatus
from apps.leads.models import Lead, LeadStatus
from apps.leads.services import LeadService
from apps.projects.models import Project
from apps.users.models import CompanyMembership, CompanyMembershipStatus

User = get_user_model()


class LeadServiceTestCase(TestCase):
    """
    Unit test suite for LeadService business logic (BE-061), mirroring
    apps.clients.tests.test_services.ClientServiceTestCase's structure.
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

        self.lead1 = LeadService.create_lead(company_id=self.company1.id, name="Jane Prospect")
        self.lead2 = LeadService.create_lead(
            company_id=self.company1.id, name="Prospect Interiors", company_name="Prospect Interiors"
        )
        self.lead3 = LeadService.create_lead(company_id=self.company2.id, name="John Other")

    # --- create ------------------------------------------------------

    def test_create_lead_success(self):
        lead = LeadService.create_lead(company_id=self.company1.id, name="New Lead", mobile="9999999999")
        self.assertEqual(lead.name, "New Lead")
        self.assertEqual(lead.company_id, self.company1.id)
        self.assertEqual(lead.mobile, "9999999999")
        self.assertEqual(lead.status, LeadStatus.NEW)

    def test_create_lead_nonexistent_company_raises_not_found(self):
        with self.assertRaises(drf_exceptions.NotFound):
            LeadService.create_lead(company_id=uuid.uuid4(), name="Orphan Lead")

    def test_create_lead_blank_name_raises_value_error(self):
        with self.assertRaises(ValueError):
            LeadService.create_lead(company_id=self.company1.id, name="   ")

    def test_create_lead_with_valid_assignee(self):
        lead = LeadService.create_lead(
            company_id=self.company1.id, name="Assigned Lead", assigned_to_id=self.sales_user.id
        )
        self.assertEqual(lead.assigned_to_id, self.sales_user.id)

    def test_create_lead_with_assignee_not_a_member_raises_validation_error(self):
        outsider = User.objects.create_user(
            email="outsider@example.com", name="Outsider", password="StrongPassword123!"
        )
        with self.assertRaises(drf_exceptions.ValidationError):
            LeadService.create_lead(
                company_id=self.company1.id, name="Bad Assignee Lead", assigned_to_id=outsider.id
            )

    def test_create_lead_duplicate_name_same_company_allowed(self):
        lead = LeadService.create_lead(company_id=self.company1.id, name="Jane Prospect")
        self.assertNotEqual(lead.id, self.lead1.id)

    def test_create_lead_writes_audit_log_entry(self):
        lead = LeadService.create_lead(company_id=self.company1.id, name="Audit Lead")

        entry = AuditLog.objects.get(entity_type="lead", entity_id=lead.id, action="create")
        self.assertEqual(entry.company_id, self.company1.id)
        self.assertIsNone(entry.before_state)
        self.assertEqual(entry.after_state["name"], "Audit Lead")
        self.assertEqual(entry.after_state["status"], LeadStatus.NEW)

    # --- get/list ------------------------------------------------------

    def test_get_lead_by_id_success(self):
        lead = LeadService.get_lead_by_id(self.lead1.id)
        self.assertEqual(lead.id, self.lead1.id)

    def test_get_lead_by_id_cross_tenant_raises_not_found(self):
        with self.assertRaises(drf_exceptions.NotFound):
            LeadService.get_lead_by_id(self.lead1.id, company_id=self.company2.id)

    def test_get_lead_by_id_nonexistent_raises_not_found(self):
        with self.assertRaises(drf_exceptions.NotFound):
            LeadService.get_lead_by_id(uuid.uuid4())

    def test_list_leads_filtering_by_company(self):
        leads_c1 = LeadService.list_leads(company_id=self.company1.id)
        self.assertEqual(leads_c1.count(), 2)

    def test_list_leads_filtering_by_status(self):
        LeadService.transition_status(self.lead1.id, LeadStatus.QUALIFIED)
        results = LeadService.list_leads(company_id=self.company1.id, status=LeadStatus.QUALIFIED)
        self.assertEqual(results.count(), 1)
        self.assertEqual(results.first().id, self.lead1.id)

    def test_list_leads_filtering_by_assigned_to(self):
        LeadService.update_lead(
            lead_id=self.lead1.id, validated_data={"assigned_to_id": self.sales_user.id}
        )
        results = LeadService.list_leads(company_id=self.company1.id, assigned_to_id=self.sales_user.id)
        self.assertEqual(results.count(), 1)
        self.assertEqual(results.first().id, self.lead1.id)

    def test_list_leads_search(self):
        results = LeadService.list_leads(search="Interiors")
        self.assertEqual(results.count(), 1)
        self.assertEqual(results.first().id, self.lead2.id)

    def test_list_leads_for_viewer_non_admin_uses_resolved_company(self):
        queryset = LeadService.list_leads_for_viewer(
            is_platform_admin=False, resolved_company_id=self.company1.id, admin_company_id_param=None
        )
        self.assertEqual(queryset.count(), 2)

    def test_list_leads_for_viewer_platform_admin_no_filter_sees_all(self):
        queryset = LeadService.list_leads_for_viewer(
            is_platform_admin=True, resolved_company_id=None, admin_company_id_param=None
        )
        self.assertEqual(queryset.count(), 3)

    # --- resolve_create_target_company_id ------------------------------

    def test_resolve_create_target_company_id_non_admin_uses_resolved(self):
        target = LeadService.resolve_create_target_company_id(
            is_platform_admin=False, resolved_company_id=self.company1.id, supplied_company_id=None
        )
        self.assertEqual(target, self.company1.id)

    def test_resolve_create_target_company_id_non_admin_mismatch_denied(self):
        with self.assertRaises(drf_exceptions.PermissionDenied):
            LeadService.resolve_create_target_company_id(
                is_platform_admin=False,
                resolved_company_id=self.company1.id,
                supplied_company_id=self.company2.id,
            )

    def test_resolve_create_target_company_id_admin_requires_company_id(self):
        with self.assertRaises(drf_exceptions.ValidationError):
            LeadService.resolve_create_target_company_id(
                is_platform_admin=True, resolved_company_id=None, supplied_company_id=None
            )

    # --- update ------------------------------------------------------

    def test_update_lead_success(self):
        updated = LeadService.update_lead(
            lead_id=self.lead1.id, validated_data={"name": "Jane Updated", "mobile": "8888888888"}
        )
        self.assertEqual(updated.name, "Jane Updated")
        self.assertEqual(updated.mobile, "8888888888")

    def test_update_lead_cross_tenant_scoping_raises_not_found(self):
        with self.assertRaises(drf_exceptions.NotFound):
            LeadService.update_lead(
                lead_id=self.lead1.id, validated_data={"name": "Hacked"}, company_id=self.company2.id
            )

    def test_update_lead_clear_assignee_with_null(self):
        LeadService.update_lead(lead_id=self.lead1.id, validated_data={"assigned_to_id": self.sales_user.id})
        updated = LeadService.update_lead(lead_id=self.lead1.id, validated_data={"assigned_to_id": None})
        self.assertIsNone(updated.assigned_to_id)

    def test_update_lead_writes_audit_log_entry_with_before_and_after(self):
        LeadService.update_lead(lead_id=self.lead1.id, validated_data={"name": "Renamed Lead"})

        entry = AuditLog.objects.filter(
            entity_type="lead", entity_id=self.lead1.id, action="update"
        ).latest("created_at")
        self.assertEqual(entry.before_state["name"], "Jane Prospect")
        self.assertEqual(entry.after_state["name"], "Renamed Lead")

    # --- delete ------------------------------------------------------

    def test_soft_delete_lead(self):
        lead_id = self.lead1.id
        LeadService.soft_delete_lead(lead_id)

        with self.assertRaises(drf_exceptions.NotFound):
            LeadService.get_lead_by_id(lead_id)

        self.assertTrue(Lead.all_objects.filter(id=lead_id).exists())

    def test_soft_delete_lead_writes_audit_log_entry(self):
        lead_id = self.lead1.id
        LeadService.soft_delete_lead(lead_id)

        entry = AuditLog.objects.get(entity_type="lead", entity_id=lead_id, action="delete")
        self.assertEqual(entry.before_state["name"], "Jane Prospect")

    # --- status transitions ------------------------------------------

    def test_transition_status_valid_forward(self):
        updated = LeadService.transition_status(self.lead1.id, LeadStatus.QUALIFIED)
        self.assertEqual(updated.status, LeadStatus.QUALIFIED)

    def test_transition_status_invalid_skip_ahead_raises_conflict(self):
        with self.assertRaises(ConflictError):
            LeadService.transition_status(self.lead1.id, LeadStatus.SITE_VISIT_SCHEDULED)

    def test_transition_status_to_won_directly_raises_conflict(self):
        """WON is never reachable via the plain status endpoint — only via convert_lead."""
        with self.assertRaises(ConflictError):
            LeadService.transition_status(self.lead1.id, LeadStatus.WON)

    def test_transition_status_to_lost_from_any_live_stage(self):
        LeadService.transition_status(self.lead1.id, LeadStatus.QUALIFIED)
        lost = LeadService.transition_status(self.lead1.id, LeadStatus.LOST)
        self.assertEqual(lost.status, LeadStatus.LOST)

    def test_transition_status_terminal_rejects_any_further_transition(self):
        LeadService.transition_status(self.lead1.id, LeadStatus.LOST)
        with self.assertRaises(ConflictError):
            LeadService.transition_status(self.lead1.id, LeadStatus.QUALIFIED)

    def test_transition_status_cross_tenant_raises_not_found(self):
        with self.assertRaises(drf_exceptions.NotFound):
            LeadService.transition_status(self.lead1.id, LeadStatus.QUALIFIED, company_id=self.company2.id)

    def test_transition_status_writes_audit_log(self):
        LeadService.transition_status(self.lead1.id, LeadStatus.QUALIFIED)
        entry = AuditLog.objects.filter(
            entity_type="lead", entity_id=self.lead1.id, action="update"
        ).latest("created_at")
        self.assertEqual(entry.before_state["status"], LeadStatus.NEW)
        self.assertEqual(entry.after_state["status"], LeadStatus.QUALIFIED)

    # --- mark_lost ------------------------------------------------------

    def test_mark_lost_success(self):
        updated = LeadService.mark_lost(self.lead1.id, loss_reason="Chose a competitor")
        self.assertEqual(updated.status, LeadStatus.LOST)
        self.assertEqual(updated.loss_reason, "Chose a competitor")

    def test_mark_lost_with_follow_up_reminder(self):
        from django.utils import timezone

        reminder = timezone.now() + timezone.timedelta(days=30)
        updated = LeadService.mark_lost(
            self.lead1.id, loss_reason="Budget too low", follow_up_reminder_at=reminder
        )
        self.assertEqual(updated.follow_up_reminder_at, reminder)

    def test_mark_lost_blank_reason_raises_value_error(self):
        with self.assertRaises(ValueError):
            LeadService.mark_lost(self.lead1.id, loss_reason="   ")

    def test_mark_lost_already_won_raises_conflict(self):
        LeadService.convert_lead(self.lead1.id)
        with self.assertRaises(ConflictError):
            LeadService.mark_lost(self.lead1.id, loss_reason="Too late")

    def test_mark_lost_already_lost_raises_conflict(self):
        LeadService.mark_lost(self.lead1.id, loss_reason="First reason")
        with self.assertRaises(ConflictError):
            LeadService.mark_lost(self.lead1.id, loss_reason="Second reason")

    # --- convert_lead ------------------------------------------------------

    def test_convert_lead_creates_client_and_sets_won(self):
        converted = LeadService.convert_lead(self.lead1.id)
        self.assertEqual(converted.status, LeadStatus.WON)
        self.assertIsNotNone(converted.converted_client_id)

        client = Client.objects.get(id=converted.converted_client_id)
        self.assertEqual(client.name, self.lead1.name)
        self.assertEqual(client.company_id, self.company1.id)
        self.assertIn("Converted from lead", client.notes)

    def test_convert_lead_with_create_project_true_also_creates_project(self):
        converted = LeadService.convert_lead(self.lead1.id, create_project=True, project_name="New Kitchen")
        self.assertIsNotNone(converted.converted_project_id)

        project = Project.objects.get(id=converted.converted_project_id)
        self.assertEqual(project.name, "New Kitchen")
        self.assertEqual(project.client_id, converted.converted_client_id)

    def test_convert_lead_without_create_project_leaves_project_null(self):
        converted = LeadService.convert_lead(self.lead1.id, create_project=False)
        self.assertIsNone(converted.converted_project_id)

    def test_convert_lead_is_idempotent(self):
        first = LeadService.convert_lead(self.lead1.id)
        client_count_after_first = Client.objects.filter(company=self.company1).count()

        second = LeadService.convert_lead(self.lead1.id)
        client_count_after_second = Client.objects.filter(company=self.company1).count()

        self.assertEqual(first.converted_client_id, second.converted_client_id)
        self.assertEqual(client_count_after_first, client_count_after_second)

    def test_convert_lead_carries_assignee_to_project(self):
        LeadService.update_lead(lead_id=self.lead1.id, validated_data={"assigned_to_id": self.sales_user.id})
        converted = LeadService.convert_lead(self.lead1.id, create_project=True)
        project = Project.objects.get(id=converted.converted_project_id)
        self.assertEqual(project.assigned_to_id, self.sales_user.id)

    def test_convert_lost_lead_raises_conflict(self):
        LeadService.mark_lost(self.lead1.id, loss_reason="Not interested")
        with self.assertRaises(ConflictError):
            LeadService.convert_lead(self.lead1.id)

    def test_convert_lead_cross_tenant_raises_not_found(self):
        with self.assertRaises(drf_exceptions.NotFound):
            LeadService.convert_lead(self.lead1.id, company_id=self.company2.id)

    def test_convert_lead_writes_single_audit_entry(self):
        before_count = AuditLog.objects.filter(entity_type="lead", entity_id=self.lead1.id).count()
        LeadService.convert_lead(self.lead1.id)
        after_count = AuditLog.objects.filter(entity_type="lead", entity_id=self.lead1.id).count()
        self.assertEqual(after_count, before_count + 1)

    def test_convert_lead_from_qualified_status_also_succeeds(self):
        LeadService.transition_status(self.lead1.id, LeadStatus.QUALIFIED)
        converted = LeadService.convert_lead(self.lead1.id)
        self.assertEqual(converted.status, LeadStatus.WON)

    def test_convert_lead_backfills_client_onto_its_linked_site_visits(self):
        from datetime import datetime, timezone as dt_timezone

        from apps.site_visits.services import SiteVisitService

        visit = SiteVisitService.create_site_visit(
            company_id=self.company1.id,
            visit_date=datetime(2026, 9, 1, tzinfo=dt_timezone.utc),
            lead_id=self.lead1.id,
        )
        self.assertIsNone(visit.client_id)

        SiteVisitService.submit_report(visit.id, company_id=self.company1.id)
        visit.refresh_from_db()
        self.assertIsNone(visit.client_id)  # not yet convertible: lead wasn't won when the report was submitted

        converted = LeadService.convert_lead(self.lead1.id)
        visit.refresh_from_db()
        self.assertEqual(visit.client_id, converted.converted_client_id)
