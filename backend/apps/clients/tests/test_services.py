import uuid
from django.test import TestCase
from rest_framework import exceptions as drf_exceptions

from apps.audit.models import AuditLog
from apps.clients.models import Client
from apps.clients.services import ClientService
from apps.company.models import Company, CompanyStatus


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
