"""
BE-069: stable system role identity (Role.system_key). Covers seeding,
the unique-per-company constraint, the API's inability to set/change it,
and the historical backfill migration's conservative signal.
"""

import datetime

from django.db import IntegrityError, transaction
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from apps.audit.models import AuditAction, AuditLog
from apps.authentication.tokens import CompanyUserAccessToken
from apps.common.test_utils import make_full_access_membership
from apps.company.models import Company, CompanyStatus
from apps.company.services import CompanyService
from apps.users.models import User, Role
from apps.users.permission_catalog import DEFAULT_ROLE_PERMISSIONS, DEFAULT_ROLE_SYSTEM_KEYS, OWNER_SYSTEM_KEY
from apps.users.services import RoleService


class SeededRoleSystemKeyTestCase(TestCase):
    """1. New company seeds stable system keys; 2. unique within company."""

    def test_new_company_seeds_a_system_key_for_every_default_role(self):
        company = CompanyService.create_company(name="Seed Test Co")
        roles = {r.name: r.system_key for r in Role.objects.filter(company=company)}
        for role_name in DEFAULT_ROLE_PERMISSIONS:
            self.assertEqual(roles[role_name], DEFAULT_ROLE_SYSTEM_KEYS[role_name])

    def test_owner_role_gets_the_owner_system_key(self):
        company = CompanyService.create_company(name="Owner Key Co")
        owner = Role.objects.get(company=company, name="Owner")
        self.assertEqual(owner.system_key, OWNER_SYSTEM_KEY)
        self.assertEqual(owner.system_key, "owner")

    def test_system_keys_unique_within_company(self):
        company = CompanyService.create_company(name="Unique Key Co")
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Role.objects.create(company=company, name="Second Owner Row", system_key="owner")

    def test_same_system_key_allowed_across_different_companies(self):
        """The uniqueness constraint is scoped per-company, not global."""
        company_a = CompanyService.create_company(name="Company A")
        company_b = CompanyService.create_company(name="Company B")
        owner_a = Role.objects.get(company=company_a, system_key="owner")
        owner_b = Role.objects.get(company=company_b, system_key="owner")
        self.assertNotEqual(owner_a.id, owner_b.id)
        self.assertEqual(owner_a.system_key, owner_b.system_key)

    def test_repeated_seeding_does_not_duplicate_roles(self):
        """Calling seed_default_roles_for_company twice for the same company must not create duplicate system-keyed roles (would violate the unique constraint)."""
        company = Company.objects.create(name="Reseed Co", status=CompanyStatus.ACTIVE)
        RoleService.seed_default_roles_for_company(company)
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                RoleService.seed_default_roles_for_company(company)


class CustomRoleSystemKeyTestCase(TestCase):
    """3. Custom role system_key is null; 6. custom role named Owner is NOT system Owner."""

    def setUp(self):
        self.company = CompanyService.create_company(name="Custom Role Co")

    def test_custom_role_has_null_system_key(self):
        role = RoleService.create_role(company_id=self.company.id, name="Bespoke Role")
        self.assertIsNone(role.system_key)

    def test_custom_role_named_owner_is_not_system_owner(self):
        """
        Renames the real seeded Owner away first (freeing the name) --
        the unique_active_role_per_company constraint would otherwise
        block creating a second "Owner"-named role outright, which is
        itself proof the ambiguity this task fixes is real: only a
        rename-then-recreate sequence can produce a same-named row.
        """
        real_owner = Role.objects.get(company=self.company, system_key="owner")
        RoleService.update_role(real_owner.id, {"name": "Owner (Renamed Away)"})

        fake_owner = RoleService.create_role(company_id=self.company.id, name="Owner")
        self.assertIsNone(fake_owner.system_key)
        self.assertNotEqual(fake_owner.id, real_owner.id)

    def test_owner_identity_survives_display_name_change(self):
        """7. Owner identity survives display-name change (rename allowed, system_key untouched)."""
        owner = Role.objects.get(company=self.company, system_key="owner")
        updated = RoleService.update_role(owner.id, {"name": "Founder"})
        self.assertEqual(updated.name, "Founder")
        self.assertEqual(updated.system_key, "owner")


class ApiCannotSetSystemKeyTestCase(TestCase):
    """4. API cannot set system_key; 5. API cannot modify system_key."""

    def setUp(self):
        self.client = APIClient()
        self.company = CompanyService.create_company(name="API Key Co")
        self.user = User.objects.create_user(email="alice@company1.com", name="Alice", password="StrongPassword123!")
        make_full_access_membership(self.company, self.user)
        self.token = str(CompanyUserAccessToken.for_user(self.user))
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token}")

    def test_create_role_ignores_system_key_in_request_body(self):
        response = self.client.post(
            "/roles",
            {"name": "Sneaky Role", "systemKey": "owner", "system_key": "owner"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        role_id = response.json()["data"]["id"]
        role = Role.objects.get(id=role_id)
        self.assertIsNone(role.system_key)
        self.assertIsNone(response.json()["data"]["systemKey"])
        self.assertFalse(response.json()["data"]["isSystem"])

    def test_update_role_cannot_inject_system_key_onto_a_custom_role(self):
        custom = RoleService.create_role(company_id=self.company.id, name="Editable Role")
        response = self.client.patch(
            f"/roles/{custom.id}",
            {"systemKey": "owner", "system_key": "owner"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        custom.refresh_from_db()
        self.assertIsNone(custom.system_key)

    def test_update_role_cannot_change_the_real_owner_role_system_key(self):
        owner = Role.objects.get(company=self.company, system_key="owner")
        response = self.client.patch(f"/roles/{owner.id}", {"systemKey": "admin"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        owner.refresh_from_db()
        self.assertEqual(owner.system_key, "owner")

    def test_role_list_exposes_system_key_and_is_system_metadata(self):
        response = self.client.get("/roles", {"pageSize": 20})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        by_name = {r["name"]: r for r in response.json()["data"]}
        self.assertEqual(by_name["Owner"]["systemKey"], "owner")
        self.assertTrue(by_name["Owner"]["isSystem"])
        # The test-fixture full-access role created in setUp is custom.
        custom_rows = [r for r in response.json()["data"] if r["systemKey"] is None]
        self.assertTrue(all(r["isSystem"] is False for r in custom_rows))


class HistoricalBackfillMigrationTestCase(TestCase):
    """
    9. Migration behavior tested where feasible -- exercises the actual
    backfill function (not the whole migration graph, matching this
    codebase's existing data-migration test precedent) against
    hand-built ambiguous scenarios the real migration must get right.
    """

    def _run_backfill(self):
        # A migration module's dotted name starts with a digit, so it
        # can't be reached via a normal `import` statement -- resolved
        # via importlib instead, matching how Django's own migration
        # loader resolves these files.
        import importlib

        from django.apps import apps as django_apps

        module = importlib.import_module("apps.users.migrations.0010_backfill_role_system_key")
        module.backfill_system_key(django_apps, None)

    def test_role_created_long_after_company_is_not_backfilled(self):
        """A hand-created role sharing a default name, created well after company creation, must stay unclassified."""
        company = Company.objects.create(name="Old Co", status=CompanyStatus.ACTIVE)
        role = Role.objects.create(company=company, name="Owner", system_key=None)
        role.created_at = company.created_at + datetime.timedelta(hours=1)
        role.save(update_fields=["created_at"])

        self._run_backfill()

        role.refresh_from_db()
        self.assertIsNone(role.system_key)

    def test_role_with_a_create_audit_row_is_not_backfilled(self):
        """A role created via the real API (audit-logged) sharing a default name is never treated as seeded, even if it happens to be created quickly."""
        company = Company.objects.create(name="Audited Co", status=CompanyStatus.ACTIVE)
        role = Role.objects.create(company=company, name="Admin", system_key=None)
        AuditLog.objects.create(
            action=AuditAction.CREATE, entity_type="role", entity_id=role.id, company=company
        )

        self._run_backfill()

        role.refresh_from_db()
        self.assertIsNone(role.system_key)

    def test_role_created_within_seconds_of_company_with_no_audit_row_is_backfilled(self):
        """The genuine seeded-role signature: fast creation, no audit row."""
        company = Company.objects.create(name="Fresh Co", status=CompanyStatus.ACTIVE)
        role = Role.objects.create(company=company, name="Owner", system_key=None)

        self._run_backfill()

        role.refresh_from_db()
        self.assertEqual(role.system_key, "owner")

    def test_backfill_is_idempotent(self):
        company = Company.objects.create(name="Idempotent Co", status=CompanyStatus.ACTIVE)
        Role.objects.create(company=company, name="Owner", system_key=None)

        self._run_backfill()
        self._run_backfill()

        self.assertEqual(
            Role.objects.filter(company=company, system_key="owner").count(), 1
        )

    def test_role_with_unrelated_name_is_never_touched(self):
        company = Company.objects.create(name="Unrelated Co", status=CompanyStatus.ACTIVE)
        role = Role.objects.create(company=company, name="Warehouse Lead", system_key=None)

        self._run_backfill()

        role.refresh_from_db()
        self.assertIsNone(role.system_key)
