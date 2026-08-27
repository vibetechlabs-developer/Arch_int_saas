import uuid
from django.test import TestCase

from apps.clients.models import Client
from apps.company.models import Company, CompanyStatus


class ClientModelTestCase(TestCase):
    """
    Unit test suite for Client domain model (BE-022).
    """

    def setUp(self):
        self.company = Company.objects.create(
            name="Test Company",
            status=CompanyStatus.ACTIVE,
        )
        self.other_company = Company.objects.create(
            name="Other Company",
            status=CompanyStatus.ACTIVE,
        )

    def test_client_creation_with_required_field_only(self):
        """
        A Client can be created with just `company` + `name` — every other
        field is optional per FRS §7 / Database_Schema.md.
        """
        client = Client.objects.create(company=self.company, name="Jane Doe")
        self.assertIsInstance(client.id, uuid.UUID)
        self.assertEqual(client.name, "Jane Doe")
        self.assertEqual(client.company, self.company)
        self.assertIsNotNone(client.created_at)
        self.assertIsNotNone(client.updated_at)
        self.assertIsNone(client.deleted_at)
        self.assertFalse(client.is_deleted)

    def test_client_optional_field_defaults(self):
        """
        Verify default values for every optional field.
        """
        client = Client.objects.create(company=self.company, name="Jane Doe")
        self.assertEqual(client.company_name, "")
        self.assertEqual(client.email, "")
        self.assertEqual(client.mobile, "")
        self.assertEqual(client.gstin, "")
        self.assertEqual(client.addresses, [])
        self.assertEqual(client.notes, "")

    def test_client_creation_with_all_fields(self):
        """
        Verify full field set persists correctly.
        """
        addresses = [
            {"label": "billing", "line1": "221B Baker St", "city": "London"},
        ]
        client = Client.objects.create(
            company=self.company,
            name="Jane Doe",
            company_name="Doe Interiors Pvt Ltd",
            email="jane@example.com",
            mobile="+91-9999999999",
            gstin="29ABCDE1234F1Z5",
            addresses=addresses,
            notes="Prefers email contact.",
        )
        client.refresh_from_db()
        self.assertEqual(client.company_name, "Doe Interiors Pvt Ltd")
        self.assertEqual(client.email, "jane@example.com")
        self.assertEqual(client.mobile, "+91-9999999999")
        self.assertEqual(client.gstin, "29ABCDE1234F1Z5")
        self.assertEqual(client.addresses, addresses)
        self.assertEqual(client.notes, "Prefers email contact.")

    def test_client_str_representation(self):
        """
        Verify string representation format: '<Client Name> (<Company Name>)'.
        """
        client = Client.objects.create(company=self.company, name="Jane Doe")
        self.assertEqual(str(client), f"Jane Doe ({self.company.name})")

    def test_client_no_uniqueness_constraint_on_name(self):
        """
        Unlike Role, Client has no documented uniqueness rule — two clients
        with an identical name in the SAME company must both save
        successfully. This asserts the absence of an invented constraint.
        """
        client1 = Client.objects.create(company=self.company, name="Jane Doe")
        client2 = Client.objects.create(company=self.company, name="Jane Doe")
        self.assertNotEqual(client1.id, client2.id)
        self.assertEqual(
            Client.objects.filter(company=self.company, name="Jane Doe").count(), 2
        )

    def test_client_same_name_different_company_allowed(self):
        """
        Verify different companies can each have a client with the same name.
        """
        client1 = Client.objects.create(company=self.company, name="Jane Doe")
        client2 = Client.objects.create(company=self.other_company, name="Jane Doe")
        self.assertEqual(client1.name, client2.name)
        self.assertNotEqual(client1.company, client2.company)

    def test_client_tenant_isolation_via_company_fk(self):
        """
        Verify a company's clients queryset only returns its own clients.
        """
        Client.objects.create(company=self.company, name="Company A Client")
        Client.objects.create(company=self.other_company, name="Company B Client")

        company_clients = Client.objects.filter(company=self.company)
        self.assertEqual(company_clients.count(), 1)
        self.assertEqual(company_clients.first().name, "Company A Client")

    def test_client_soft_delete_lifecycle(self):
        """
        Verify soft delete lifecycle (deleted_at set, excluded from default
        manager, restore).
        """
        client = Client.objects.create(company=self.company, name="Jane Doe")
        client_id = client.id

        client.delete()
        self.assertTrue(client.is_deleted)
        self.assertIsNotNone(client.deleted_at)

        self.assertFalse(Client.objects.filter(id=client_id).exists())
        self.assertTrue(Client.all_objects.filter(id=client_id).exists())
        self.assertTrue(Client.deleted_objects.filter(id=client_id).exists())

        client.restore()
        self.assertFalse(client.is_deleted)
        self.assertIsNone(client.deleted_at)
        self.assertTrue(Client.objects.filter(id=client_id).exists())

    def test_client_cascade_delete_with_company(self):
        """
        Verify cascade deletion of clients when parent Company is hard deleted.
        """
        client = Client.objects.create(company=self.company, name="Jane Doe")
        client_id = client.id
        self.company.delete(hard=True)
        self.assertFalse(Client.all_objects.filter(id=client_id).exists())

    def test_client_requires_company(self):
        """
        Verify `company` is a required (NOT NULL) field.
        """
        with self.assertRaises(Exception):
            Client.objects.create(name="No Company Client")
