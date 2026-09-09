import uuid
from django.test import TestCase
from rest_framework import exceptions as drf_exceptions

from apps.audit.models import AuditLog
from apps.common.exceptions import ConflictError
from apps.company.models import Company, CompanyStatus
from apps.users.models import Role
from apps.users.services import RoleService


class RoleServiceTestCase(TestCase):
    """
    Unit test suite for RoleService business logic (BE-014).
    """

    def setUp(self):
        self.company1 = Company.objects.create(
            name="Alpha Corp",
            status=CompanyStatus.ACTIVE,
        )
        self.company2 = Company.objects.create(
            name="Beta Corp",
            status=CompanyStatus.ACTIVE,
        )

        self.role1 = RoleService.create_role(
            company_id=self.company1.id,
            name="Project Manager",
            description="Manages projects",
            is_active=True,
        )
        self.role2 = RoleService.create_role(
            company_id=self.company1.id,
            name="Interior Designer",
            description="Designs interiors",
            is_active=False,
        )
        self.role3 = RoleService.create_role(
            company_id=self.company2.id,
            name="Site Supervisor",
            description="Supervises sites",
            is_active=True,
        )

    def test_create_role_success(self):
        """
        Verify RoleService creates a role with proper fields.
        """
        role = RoleService.create_role(
            company_id=self.company1.id,
            name="3D Visualizer",
            description="Creates 3D models",
            is_active=True,
        )
        self.assertEqual(role.name, "3D Visualizer")
        self.assertEqual(role.company_id, self.company1.id)
        self.assertTrue(role.is_active)

    def test_create_role_duplicate_name_raises_conflict(self):
        """
        Verify creating a role with a duplicate name within the same company raises ConflictError (409).
        """
        with self.assertRaises(ConflictError):
            RoleService.create_role(
                company_id=self.company1.id,
                name="Project Manager",
            )

        # Case-insensitive check
        with self.assertRaises(ConflictError):
            RoleService.create_role(
                company_id=self.company1.id,
                name="project manager",
            )

    def test_create_role_nonexistent_company_raises_not_found(self):
        """
        Verify creating a role for non-existent company raises NotFound (404).
        """
        with self.assertRaises(drf_exceptions.NotFound):
            RoleService.create_role(
                company_id=uuid.uuid4(),
                name="New Role",
            )

    def test_get_role_by_id_success(self):
        """
        Verify retrieving an active role by ID.
        """
        role = RoleService.get_role_by_id(self.role1.id)
        self.assertEqual(role.id, self.role1.id)
        self.assertEqual(role.name, "Project Manager")

    def test_get_role_by_id_with_company_scoping(self):
        """
        Verify tenant-scoped get_role_by_id raises NotFound for cross-tenant query.
        """
        # Role 1 belongs to Company 1; requesting with Company 2 raises NotFound
        with self.assertRaises(drf_exceptions.NotFound):
            RoleService.get_role_by_id(self.role1.id, company_id=self.company2.id)

    def test_get_role_by_id_nonexistent_raises_not_found(self):
        """
        Verify retrieving non-existent role raises NotFound (404).
        """
        with self.assertRaises(drf_exceptions.NotFound):
            RoleService.get_role_by_id(uuid.uuid4())

    def test_list_roles_filtering_and_search(self):
        """
        Verify list_roles filtering by company, active status, search, and ordering.
        """
        # Filter by company 1
        roles_c1 = RoleService.list_roles(company_id=self.company1.id)
        self.assertEqual(roles_c1.count(), 2)

        # Filter by active status
        roles_active = RoleService.list_roles(company_id=self.company1.id, is_active=True)
        self.assertEqual(roles_active.count(), 1)
        self.assertEqual(roles_active.first().name, "Project Manager")

        # Search query
        roles_search = RoleService.list_roles(search="Designer")
        self.assertEqual(roles_search.count(), 1)
        self.assertEqual(roles_search.first().name, "Interior Designer")

    def test_update_role_success(self):
        """
        Verify updating role attributes.
        """
        updated = RoleService.update_role(
            role_id=self.role1.id,
            validated_data={
                "name": "Senior Project Manager",
                "description": "Updated description",
                "is_active": False,
            },
        )
        self.assertEqual(updated.name, "Senior Project Manager")
        self.assertEqual(updated.description, "Updated description")
        self.assertFalse(updated.is_active)

    def test_update_role_duplicate_name_raises_conflict(self):
        """
        Verify updating role to an existing role's name raises ConflictError.
        """
        with self.assertRaises(ConflictError):
            RoleService.update_role(
                role_id=self.role1.id,
                validated_data={"name": "Interior Designer"},
            )

    def test_soft_delete_role(self):
        """
        Verify soft-deleting a role removes it from active queries.
        """
        role_id = self.role1.id
        RoleService.soft_delete_role(role_id)

        # Subsequent retrieval raises NotFound
        with self.assertRaises(drf_exceptions.NotFound):
            RoleService.get_role_by_id(role_id)

        # Still exists in all_objects
        self.assertTrue(Role.all_objects.filter(id=role_id).exists())

    def test_create_role_writes_audit_log_entry(self):
        """
        BE-019: RoleService.create_role now routes through AuditLogService
        instead of a bare audit_logger.info() call — verify the durable row.
        """
        role = RoleService.create_role(
            company_id=self.company1.id,
            name="Audit Coverage Role",
        )

        entry = AuditLog.objects.get(entity_type="role", entity_id=role.id)
        self.assertEqual(entry.action, "create")
        self.assertEqual(entry.company_id, self.company1.id)
        self.assertIsNone(entry.before_state)
        self.assertEqual(entry.after_state["name"], "Audit Coverage Role")

    def test_update_role_writes_audit_log_entry_with_before_and_after(self):
        RoleService.update_role(
            role_id=self.role1.id,
            validated_data={"name": "Renamed Role"},
        )

        entry = AuditLog.objects.filter(
            entity_type="role", entity_id=self.role1.id, action="update"
        ).latest("created_at")
        self.assertEqual(entry.before_state["name"], "Project Manager")
        self.assertEqual(entry.after_state["name"], "Renamed Role")

    def test_soft_delete_role_writes_audit_log_entry(self):
        role_id = self.role1.id
        RoleService.soft_delete_role(role_id)

        entry = AuditLog.objects.get(entity_type="role", entity_id=role_id, action="delete")
        self.assertEqual(entry.before_state["name"], "Project Manager")
        self.assertIsNone(entry.after_state)

    def test_soft_delete_role_unassigns_members_holding_it(self):
        """
        BE-073: deleting a role that is still assigned to an active
        membership must not leave that membership silently pointing at a
        role invisible everywhere else in the API. Soft-delete never
        triggers Django's on_delete=SET_NULL (that only fires on a real DB
        DELETE), so RoleService.soft_delete_role must replicate that FK's
        own declared intent itself.
        """
        from apps.users.models import CompanyMembership, CompanyMembershipStatus, User

        user = User.objects.create_user(
            email="role-delete-safety@example.com", name="Holder", password="Xx!12345678"
        )
        membership = CompanyMembership.objects.create(
            company=self.company1,
            user=user,
            role=self.role1,
            status=CompanyMembershipStatus.ACTIVE,
        )

        RoleService.soft_delete_role(self.role1.id)

        membership.refresh_from_db()
        self.assertIsNone(membership.role_id)

    def test_soft_delete_role_revokes_effective_permissions_for_holders(self):
        """
        BE-073: the authorization-relevant end state — a member holding a
        deleted role must end up with zero effective permission codes, not
        merely a cosmetically-cleared roleId.
        """
        from apps.users.models import (
            CompanyMembership,
            CompanyMembershipStatus,
            Permission,
            RolePermission,
            User,
        )
        from apps.users.services import PermissionService

        permission = Permission.objects.first()
        RolePermission.objects.create(role=self.role1, permission=permission)

        user = User.objects.create_user(
            email="role-delete-safety-2@example.com", name="Holder", password="Xx!12345678"
        )
        membership = CompanyMembership.objects.create(
            company=self.company1,
            user=user,
            role=self.role1,
            status=CompanyMembershipStatus.ACTIVE,
        )

        before = PermissionService.get_permission_codes_for_membership(
            CompanyMembership.objects.select_related("role").get(id=membership.id)
        )
        self.assertIn(permission.code, before)

        RoleService.soft_delete_role(self.role1.id)

        after = PermissionService.get_permission_codes_for_membership(
            CompanyMembership.objects.select_related("role").get(id=membership.id)
        )
        self.assertEqual(after, set())

    def test_soft_delete_role_leaves_other_memberships_untouched(self):
        """
        The unassign-on-delete bulk update must be scoped to the deleted
        role only — a membership on a different, still-active role must
        keep its role assignment.
        """
        from apps.users.models import CompanyMembership, CompanyMembershipStatus, User

        user = User.objects.create_user(
            email="role-delete-safety-3@example.com", name="Other Holder", password="Xx!12345678"
        )
        untouched_membership = CompanyMembership.objects.create(
            company=self.company1,
            user=user,
            role=self.role2,
            status=CompanyMembershipStatus.ACTIVE,
        )

        RoleService.soft_delete_role(self.role1.id)

        untouched_membership.refresh_from_db()
        self.assertEqual(untouched_membership.role_id, self.role2.id)

    def test_soft_delete_role_audit_log_records_unassigned_count(self):
        from apps.users.models import CompanyMembership, CompanyMembershipStatus, User

        user = User.objects.create_user(
            email="role-delete-safety-4@example.com", name="Holder", password="Xx!12345678"
        )
        CompanyMembership.objects.create(
            company=self.company1,
            user=user,
            role=self.role1,
            status=CompanyMembershipStatus.ACTIVE,
        )

        RoleService.soft_delete_role(self.role1.id)

        entry = AuditLog.objects.get(entity_type="role", entity_id=self.role1.id, action="delete")
        self.assertEqual(entry.before_state["memberships_unassigned"], 1)
