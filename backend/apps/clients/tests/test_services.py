import uuid
from django.test import TestCase
from rest_framework import exceptions as drf_exceptions

from apps.audit.models import AuditLog
from apps.clients.models import Client
from apps.clients.services import ClientService
from apps.common.exceptions import ConflictError
from apps.company.models import Company, CompanyStatus
from apps.projects.models import Project, ProjectStatus


class ClientServiceTestCase(TestCase):
    """
    Unit test suite for ClientService business logic (BE-023).
    """

    def setUp(self):
        self.company1 = Company.objects.create(name="Alpha Corp", status=CompanyStatus.ACTIVE)
        self.company2 = Company.objects.create(name="Beta Corp", status=CompanyStatus.ACTIVE)

        self.client1 = ClientService.create_client(
            company_id=self.company1.id,
            name="Jane Doe",
            email="jane@example.com",
        )
        self.client2 = ClientService.create_client(
            company_id=self.company1.id,
            name="Interior Designs Ltd",
            company_name="Interior Designs Ltd",
        )
        self.client3 = ClientService.create_client(
            company_id=self.company2.id,
            name="John Smith",
        )

    def test_create_client_success(self):
        client = ClientService.create_client(
            company_id=self.company1.id,
            name="New Client",
            mobile="9999999999",
        )
        self.assertEqual(client.name, "New Client")
        self.assertEqual(client.company_id, self.company1.id)
        self.assertEqual(client.mobile, "9999999999")

    def test_create_client_nonexistent_company_raises_not_found(self):
        with self.assertRaises(drf_exceptions.NotFound):
            ClientService.create_client(company_id=uuid.uuid4(), name="Orphan Client")

    def test_create_client_duplicate_name_same_company_allowed(self):
        """
        Unlike Role, Client has no uniqueness constraint — creating two
        clients with the same name in the same company must succeed.
        """
        client = ClientService.create_client(company_id=self.company1.id, name="Jane Doe")
        self.assertNotEqual(client.id, self.client1.id)

    def test_get_client_by_id_success(self):
        client = ClientService.get_client_by_id(self.client1.id)
        self.assertEqual(client.id, self.client1.id)

    def test_get_client_by_id_with_company_scoping_cross_tenant_raises_not_found(self):
        with self.assertRaises(drf_exceptions.NotFound):
            ClientService.get_client_by_id(self.client1.id, company_id=self.company2.id)

    def test_get_client_by_id_nonexistent_raises_not_found(self):
        with self.assertRaises(drf_exceptions.NotFound):
            ClientService.get_client_by_id(uuid.uuid4())

    def test_list_clients_filtering_by_company(self):
        clients_c1 = ClientService.list_clients(company_id=self.company1.id)
        self.assertEqual(clients_c1.count(), 2)

    def test_list_clients_search(self):
        results = ClientService.list_clients(search="Interior")
        self.assertEqual(results.count(), 1)
        self.assertEqual(results.first().name, "Interior Designs Ltd")

        results_email = ClientService.list_clients(search="jane@example.com")
        self.assertEqual(results_email.count(), 1)
        self.assertEqual(results_email.first().id, self.client1.id)

    def test_list_clients_for_viewer_non_admin_uses_resolved_company(self):
        queryset = ClientService.list_clients_for_viewer(
            is_platform_admin=False,
            resolved_company_id=self.company1.id,
            admin_company_id_param=None,
        )
        self.assertEqual(queryset.count(), 2)

    def test_list_clients_for_viewer_platform_admin_no_filter_sees_all(self):
        queryset = ClientService.list_clients_for_viewer(
            is_platform_admin=True,
            resolved_company_id=None,
            admin_company_id_param=None,
        )
        self.assertEqual(queryset.count(), 3)

    def test_resolve_create_target_company_id_non_admin_uses_resolved(self):
        target = ClientService.resolve_create_target_company_id(
            is_platform_admin=False,
            resolved_company_id=self.company1.id,
            supplied_company_id=None,
        )
        self.assertEqual(target, self.company1.id)

    def test_resolve_create_target_company_id_non_admin_mismatch_denied(self):
        with self.assertRaises(drf_exceptions.PermissionDenied):
            ClientService.resolve_create_target_company_id(
                is_platform_admin=False,
                resolved_company_id=self.company1.id,
                supplied_company_id=self.company2.id,
            )

    def test_resolve_create_target_company_id_admin_requires_company_id(self):
        with self.assertRaises(drf_exceptions.ValidationError):
            ClientService.resolve_create_target_company_id(
                is_platform_admin=True,
                resolved_company_id=None,
                supplied_company_id=None,
            )

    def test_resolve_create_target_company_id_admin_with_company_id(self):
        target = ClientService.resolve_create_target_company_id(
            is_platform_admin=True,
            resolved_company_id=None,
            supplied_company_id=self.company2.id,
        )
        self.assertEqual(target, self.company2.id)

    def test_update_client_success(self):
        updated = ClientService.update_client(
            client_id=self.client1.id,
            validated_data={"name": "Jane Updated", "mobile": "8888888888"},
        )
        self.assertEqual(updated.name, "Jane Updated")
        self.assertEqual(updated.mobile, "8888888888")

    def test_update_client_cross_tenant_scoping_raises_not_found(self):
        with self.assertRaises(drf_exceptions.NotFound):
            ClientService.update_client(
                client_id=self.client1.id,
                validated_data={"name": "Hacked"},
                company_id=self.company2.id,
            )

    def test_soft_delete_client(self):
        client_id = self.client1.id
        ClientService.soft_delete_client(client_id)

        with self.assertRaises(drf_exceptions.NotFound):
            ClientService.get_client_by_id(client_id)

        self.assertTrue(Client.all_objects.filter(id=client_id).exists())

    def test_create_client_writes_audit_log_entry(self):
        client = ClientService.create_client(company_id=self.company1.id, name="Audit Client")

        entry = AuditLog.objects.get(entity_type="client", entity_id=client.id, action="create")
        self.assertEqual(entry.company_id, self.company1.id)
        self.assertIsNone(entry.before_state)
        self.assertEqual(entry.after_state["name"], "Audit Client")

    def test_create_client_audit_excludes_addresses_and_notes(self):
        """
        ENTITY_FIELD_ALLOWLISTS["client"] deliberately excludes
        addresses/notes for this MVP audit payload (BE-023 decision #13).
        """
        client = ClientService.create_client(
            company_id=self.company1.id,
            name="Private Client",
            notes="Sensitive internal note",
            addresses=[{"line1": "secret address"}],
        )

        entry = AuditLog.objects.get(entity_type="client", entity_id=client.id, action="create")
        self.assertNotIn("notes", entry.after_state)
        self.assertNotIn("addresses", entry.after_state)

    def test_update_client_writes_audit_log_entry_with_before_and_after(self):
        ClientService.update_client(
            client_id=self.client1.id,
            validated_data={"name": "Renamed Client"},
        )

        entry = AuditLog.objects.filter(
            entity_type="client", entity_id=self.client1.id, action="update"
        ).latest("created_at")
        self.assertEqual(entry.before_state["name"], "Jane Doe")
        self.assertEqual(entry.after_state["name"], "Renamed Client")

    def test_soft_delete_client_writes_audit_log_entry(self):
        client_id = self.client1.id
        ClientService.soft_delete_client(client_id)

        entry = AuditLog.objects.get(entity_type="client", entity_id=client_id, action="delete")
        self.assertEqual(entry.before_state["name"], "Jane Doe")
        self.assertIsNone(entry.after_state)


class ClientDeleteGuardTestCase(TestCase):
    """
    BE-024: resolves the BE-022/BE-023 deferral. A Client with any Project
    not in a terminal status (completed/cancelled) must not be
    soft-deleted. Terminal/blocking status sets per Backend Lead decision
    (2026-08-27).
    """

    def setUp(self):
        self.company = Company.objects.create(name="Guard Co", status=CompanyStatus.ACTIVE)
        self.client_obj = Client.objects.create(company=self.company, name="Guarded Client")

    def _make_project(self, status: str) -> Project:
        return Project.objects.create(
            company=self.company, client=self.client_obj, name=f"Project {status}", status=status
        )

    def test_delete_succeeds_with_zero_projects(self):
        ClientService.soft_delete_client(self.client_obj.id)
        self.client_obj.refresh_from_db()
        self.assertTrue(self.client_obj.is_deleted)

    def test_delete_succeeds_with_completed_only(self):
        self._make_project(ProjectStatus.COMPLETED)
        ClientService.soft_delete_client(self.client_obj.id)
        self.client_obj.refresh_from_db()
        self.assertTrue(self.client_obj.is_deleted)

    def test_delete_succeeds_with_cancelled_only(self):
        self._make_project(ProjectStatus.CANCELLED)
        ClientService.soft_delete_client(self.client_obj.id)
        self.client_obj.refresh_from_db()
        self.assertTrue(self.client_obj.is_deleted)

    def test_delete_succeeds_with_completed_and_cancelled(self):
        self._make_project(ProjectStatus.COMPLETED)
        self._make_project(ProjectStatus.CANCELLED)
        ClientService.soft_delete_client(self.client_obj.id)
        self.client_obj.refresh_from_db()
        self.assertTrue(self.client_obj.is_deleted)

    def test_delete_blocked_by_draft_project(self):
        self._make_project(ProjectStatus.DRAFT)
        with self.assertRaises(ConflictError):
            ClientService.soft_delete_client(self.client_obj.id)

    def test_delete_blocked_by_planning_project(self):
        self._make_project(ProjectStatus.PLANNING)
        with self.assertRaises(ConflictError):
            ClientService.soft_delete_client(self.client_obj.id)

    def test_delete_blocked_by_design_project(self):
        self._make_project(ProjectStatus.DESIGN)
        with self.assertRaises(ConflictError):
            ClientService.soft_delete_client(self.client_obj.id)

    def test_delete_blocked_by_quotation_project(self):
        self._make_project(ProjectStatus.QUOTATION)
        with self.assertRaises(ConflictError):
            ClientService.soft_delete_client(self.client_obj.id)

    def test_delete_blocked_by_approved_project(self):
        self._make_project(ProjectStatus.APPROVED)
        with self.assertRaises(ConflictError):
            ClientService.soft_delete_client(self.client_obj.id)

    def test_delete_blocked_by_execution_project(self):
        self._make_project(ProjectStatus.EXECUTION)
        with self.assertRaises(ConflictError):
            ClientService.soft_delete_client(self.client_obj.id)

    def test_delete_blocked_by_quality_check_project(self):
        self._make_project(ProjectStatus.QUALITY_CHECK)
        with self.assertRaises(ConflictError):
            ClientService.soft_delete_client(self.client_obj.id)

    def test_delete_blocked_by_handover_project(self):
        self._make_project(ProjectStatus.HANDOVER)
        with self.assertRaises(ConflictError):
            ClientService.soft_delete_client(self.client_obj.id)

    def test_delete_blocked_by_on_hold_project(self):
        self._make_project(ProjectStatus.ON_HOLD)
        with self.assertRaises(ConflictError):
            ClientService.soft_delete_client(self.client_obj.id)

    def test_blocked_delete_leaves_client_undeleted(self):
        self._make_project(ProjectStatus.DRAFT)
        with self.assertRaises(ConflictError):
            ClientService.soft_delete_client(self.client_obj.id)

        self.client_obj.refresh_from_db()
        self.assertFalse(self.client_obj.is_deleted)
        self.assertIsNone(self.client_obj.deleted_at)

    def test_blocked_delete_does_not_write_delete_audit_entry(self):
        self._make_project(ProjectStatus.DRAFT)
        with self.assertRaises(ConflictError):
            ClientService.soft_delete_client(self.client_obj.id)

        self.assertFalse(
            AuditLog.objects.filter(
                entity_type="client", entity_id=self.client_obj.id, action="delete"
            ).exists()
        )

    def test_successful_delete_still_writes_audit_entry(self):
        self._make_project(ProjectStatus.COMPLETED)
        ClientService.soft_delete_client(self.client_obj.id)

        self.assertTrue(
            AuditLog.objects.filter(
                entity_type="client", entity_id=self.client_obj.id, action="delete"
            ).exists()
        )
