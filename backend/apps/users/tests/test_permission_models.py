import uuid

from django.db import IntegrityError
from django.test import TestCase

from apps.company.models import Company, CompanyStatus
from apps.users.models import Permission, Role, RolePermission
from apps.users.permission_catalog import ALL_PERMISSION_CODES, PERMISSION_CATALOG


class PermissionCatalogMigrationTestCase(TestCase):
    """
    Verifies the 0005 data migration actually seeded the documented
    Permission catalog (BE-049).
    """

    def test_catalog_is_seeded(self):
        self.assertEqual(Permission.objects.count(), len(PERMISSION_CATALOG))
        for code in ALL_PERMISSION_CODES:
            self.assertTrue(
                Permission.objects.filter(code=code).exists(), f"missing seeded code: {code}"
            )

    def test_codes_are_unique(self):
        self.assertEqual(len(ALL_PERMISSION_CODES), len(set(ALL_PERMISSION_CODES)))

    def test_permission_code_format(self):
        for permission in Permission.objects.all():
            self.assertEqual(permission.code, f"{permission.module}.{permission.action}")


class RolePermissionModelTestCase(TestCase):
    """
    Unit tests for the RolePermission join model (BE-049).
    """

    def setUp(self):
        self.company = Company.objects.create(name="Alpha Corp", status=CompanyStatus.ACTIVE)
        self.role = Role.objects.create(company=self.company, name="Custom Role", is_active=True)
        self.permission = Permission.objects.get(code="project.view")

    def test_grant_permission_to_role(self):
        grant = RolePermission.objects.create(role=self.role, permission=self.permission)
        self.assertIsInstance(grant.id, uuid.UUID)
        self.assertIn(grant, self.role.role_permissions.all())

    def test_duplicate_active_grant_raises_integrity_error(self):
        RolePermission.objects.create(role=self.role, permission=self.permission)
        with self.assertRaises(IntegrityError):
            RolePermission.objects.create(role=self.role, permission=self.permission)

    def test_soft_deleted_grant_can_be_re_granted(self):
        grant = RolePermission.objects.create(role=self.role, permission=self.permission)
        grant.delete()
        # Should not raise -- the unique constraint is conditioned on
        # deleted_at__isnull=True, so a soft-deleted grant doesn't block a
        # fresh one.
        RolePermission.objects.create(role=self.role, permission=self.permission)

    def test_role_permission_cascade_on_role_hard_delete(self):
        RolePermission.objects.create(role=self.role, permission=self.permission)
        self.role.hard_delete()
        self.assertEqual(RolePermission.all_objects.count(), 0)


class CompanyMembershipRoleFieldTestCase(TestCase):
    """
    Unit tests for CompanyMembership's new `role` FK (BE-050).
    """

    def setUp(self):
        from django.contrib.auth import get_user_model

        User = get_user_model()
        self.company = Company.objects.create(name="Alpha Corp", status=CompanyStatus.ACTIVE)
        self.user = User.objects.create_user(
            email="member@example.com", name="Member", password="StrongPassword123!"
        )
        self.role = Role.objects.create(company=self.company, name="Accountant", is_active=True)

    def test_membership_role_defaults_to_none(self):
        from apps.users.models import CompanyMembership

        membership = CompanyMembership.objects.create(company=self.company, user=self.user)
        self.assertIsNone(membership.role)

    def test_membership_role_assignment(self):
        from apps.users.models import CompanyMembership

        membership = CompanyMembership.objects.create(
            company=self.company, user=self.user, role=self.role
        )
        self.assertEqual(membership.role, self.role)

    def test_role_deletion_sets_membership_role_to_null(self):
        from apps.users.models import CompanyMembership

        membership = CompanyMembership.objects.create(
            company=self.company, user=self.user, role=self.role
        )
        self.role.hard_delete()
        membership.refresh_from_db()
        self.assertIsNone(membership.role)
