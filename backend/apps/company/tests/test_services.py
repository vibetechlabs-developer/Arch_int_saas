import uuid
from django.test import TestCase
from rest_framework.exceptions import NotFound

from apps.audit.models import AuditLog
from apps.company.models import Company, CompanyStatus
from apps.company.services import CompanyService


class CompanyServiceTestCase(TestCase):
    """
    Unit tests for CompanyService business logic (BE-011).
    """

    def setUp(self):
        self.company, _ = CompanyService.create_company(
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
        c, _ = CompanyService.create_company(name="Standard Design Studio")
        self.assertIsInstance(c.id, uuid.UUID)
        self.assertEqual(c.name, "Standard Design Studio")
        self.assertEqual(c.status, "trial")
        self.assertEqual(c.currency, "INR")
        self.assertIsNone(c.gst_number)
        self.assertIn("numbering", c.settings)

    def test_create_company_auto_seeds_default_roles(self):
        """
        BE-049: a new company isn't empty-handed -- the documented default
        roles (05_Security/Permissions.md §3) are auto-created, each with
        its representative permission set.
        """
        from apps.users.models import Role
        from apps.users.permission_catalog import DEFAULT_ROLE_PERMISSIONS
        from apps.users.repositories import PermissionRepository

        c, _ = CompanyService.create_company(name="Fresh Tenant Co")

        seeded_names = set(Role.objects.filter(company=c).values_list("name", flat=True))
        self.assertEqual(seeded_names, set(DEFAULT_ROLE_PERMISSIONS.keys()))

        owner_role = Role.objects.get(company=c, name="Owner")
        self.assertTrue(len(PermissionRepository.codes_for_role(owner_role.id)) > 0)

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
        company, _ = CompanyService.create_company(
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

    def test_create_company_writes_audit_log_entry(self):
        """
        BE-019: CompanyService.create_company had no audit logging at all
        before this task — verify the durable row now exists.
        """
        company, _ = CompanyService.create_company(name="Audit Coverage Co")

        entry = AuditLog.objects.get(entity_type="company", entity_id=company.id, action="create")
        self.assertEqual(entry.company_id, company.id)
        self.assertIsNone(entry.before_state)
        self.assertEqual(entry.after_state["name"], "Audit Coverage Co")

    def test_update_company_writes_audit_log_entry_with_before_and_after(self):
        CompanyService.update_company(
            company_id=self.company.id,
            validated_data={"name": "Renamed Co"},
            is_platform_admin=False,
        )

        entry = AuditLog.objects.filter(
            entity_type="company", entity_id=self.company.id, action="update"
        ).latest("created_at")
        self.assertEqual(entry.before_state["name"], "Apex Interiors")
        self.assertEqual(entry.after_state["name"], "Renamed Co")

    def test_status_change_visible_in_update_audit_entry(self):
        """
        A status change is not a distinct AuditAction — it's an UPDATE with
        the "status" key differing between before_state and after_state.
        """
        CompanyService.update_company(
            company_id=self.company.id,
            validated_data={"status": "suspended"},
            is_platform_admin=True,
        )

        entry = AuditLog.objects.filter(
            entity_type="company", entity_id=self.company.id, action="update"
        ).latest("created_at")
        self.assertEqual(entry.before_state["status"], "active")
        self.assertEqual(entry.after_state["status"], "suspended")

    def test_soft_delete_company_writes_audit_log_entry(self):
        c_id = self.company.id
        CompanyService.soft_delete_company(c_id)

        entry = AuditLog.objects.get(entity_type="company", entity_id=c_id, action="delete")
        self.assertEqual(entry.before_state["name"], "Apex Interiors")
        self.assertIsNone(entry.after_state)


class CompanyServiceOwnerCreationTestCase(TestCase):
    """
    Unit tests for CompanyService.create_company's optional owner_email/
    owner_name (closes the gap flagged when the Platform Console shipped,
    F48/BACKEND_TASKS.md) — reuses CompanyMembershipService.add_user
    (BE-071), so these tests focus on the wiring (owner role resolved,
    membership actually created, response flags correct), not re-testing
    add_user's own already-covered behavior.
    """

    def test_create_company_without_owner_fields_leaves_it_empty_unchanged(self):
        from apps.users.models import CompanyMembership

        company, owner_result = CompanyService.create_company(name="No Owner Co")
        self.assertIsNone(owner_result)
        self.assertEqual(CompanyMembership.objects.filter(company=company).count(), 0)

    def test_create_company_with_owner_fields_grants_the_owner_role(self):
        from apps.users.models import CompanyMembership, CompanyMembershipStatus, Role
        from apps.users.permission_catalog import OWNER_SYSTEM_KEY

        company, owner_result = CompanyService.create_company(
            name="Fresh Studio", owner_email="newowner@example.com", owner_name="New Owner"
        )

        self.assertEqual(owner_result, {"userCreated": True, "activationRequired": True})

        owner_role = Role.objects.get(company=company, system_key=OWNER_SYSTEM_KEY)
        membership = CompanyMembership.objects.get(company=company, role=owner_role)
        self.assertEqual(membership.user.email, "newowner@example.com")
        self.assertEqual(membership.user.name, "New Owner")
        self.assertEqual(membership.status, CompanyMembershipStatus.ACTIVE)
        self.assertFalse(membership.user.has_usable_password())

    def test_create_company_with_owner_links_an_existing_user_without_duplicating(self):
        from django.contrib.auth import get_user_model

        User = get_user_model()
        existing = User.objects.create_user(email="already@example.com", name="Already Here", password="x")

        company, owner_result = CompanyService.create_company(
            name="Second Studio", owner_email="already@example.com", owner_name="Already Here"
        )

        self.assertFalse(owner_result["userCreated"])
        self.assertEqual(User.objects.filter(email="already@example.com").count(), 1)
        from apps.users.models import CompanyMembership

        self.assertTrue(CompanyMembership.objects.filter(company=company, user=existing).exists())

    def test_create_company_owner_writes_audit_log_entry_for_the_membership(self):
        from apps.audit.models import AuditLog

        company, _ = CompanyService.create_company(
            name="Audited Owner Co", owner_email="audited@example.com", owner_name="Audited Owner"
        )

        self.assertTrue(
            AuditLog.objects.filter(
                entity_type="company_membership", company_id=company.id, action="create"
            ).exists()
        )
