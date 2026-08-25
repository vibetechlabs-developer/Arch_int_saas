import uuid
from django.db import IntegrityError
from django.test import TestCase
from django.utils import timezone

from apps.company.models import Company, CompanyStatus
from apps.users.models import Role


class RoleModelTestCase(TestCase):
    """
    Unit test suite for Role domain model (BE-012/BE-014).
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

    def test_role_creation_with_defaults(self):
        """
        Verify Role creation with default attributes (UUID, is_active=True, created_at/updated_at).
        """
        role = Role.objects.create(
            company=self.company,
            name="Project Manager",
            description="Manages architectural projects",
        )
        self.assertIsInstance(role.id, uuid.UUID)
        self.assertEqual(role.name, "Project Manager")
        self.assertEqual(role.description, "Manages architectural projects")
        self.assertEqual(role.company, self.company)
        self.assertTrue(role.is_active)
        self.assertIsNotNone(role.created_at)
        self.assertIsNotNone(role.updated_at)
        self.assertIsNone(role.deleted_at)
        self.assertFalse(role.is_deleted)

    def test_role_str_representation(self):
        """
        Verify string representation format: '<Role Name> (<Company Name>)'.
        """
        role = Role.objects.create(
            company=self.company,
            name="Architect",
        )
        self.assertEqual(str(role), f"Architect ({self.company.name})")

    def test_role_unique_name_per_company_constraint(self):
        """
        Verify unique active role name per company constraint is enforced.
        """
        Role.objects.create(
            company=self.company,
            name="Lead Designer",
        )

        with self.assertRaises(IntegrityError):
            Role.objects.create(
                company=self.company,
                name="Lead Designer",
            )

    def test_role_same_name_different_company_allowed(self):
        """
        Verify that different companies can have roles with the same name.
        """
        role1 = Role.objects.create(
            company=self.company,
            name="Designer",
        )
        role2 = Role.objects.create(
            company=self.other_company,
            name="Designer",
        )
        self.assertEqual(role1.name, role2.name)
        self.assertNotEqual(role1.company, role2.company)

    def test_role_soft_delete_lifecycle(self):
        """
        Verify soft delete lifecycle (deleted_at set, excluded from default manager, restore).
        """
        role = Role.objects.create(
            company=self.company,
            name="Junior Designer",
        )
        role_id = role.id

        # Soft delete
        role.delete()
        self.assertTrue(role.is_deleted)
        self.assertIsNotNone(role.deleted_at)

        # Excluded from default manager
        self.assertFalse(Role.objects.filter(id=role_id).exists())
        # Included in all_objects and deleted_objects
        self.assertTrue(Role.all_objects.filter(id=role_id).exists())
        self.assertTrue(Role.deleted_objects.filter(id=role_id).exists())

        # Soft-deleted role allows new role with same name to be created
        new_role = Role.objects.create(
            company=self.company,
            name="Junior Designer",
        )
        self.assertEqual(new_role.name, "Junior Designer")
        self.assertNotEqual(new_role.id, role_id)

        # Restore original role (after deleting new one to prevent constraint violation)
        new_role.delete(hard=True)
        role.restore()
        self.assertFalse(role.is_deleted)
        self.assertIsNone(role.deleted_at)
        self.assertTrue(Role.objects.filter(id=role_id).exists())

    def test_role_cascade_delete_with_company(self):
        """
        Verify cascade deletion of roles when parent Company is hard deleted.
        """
        role = Role.objects.create(
            company=self.company,
            name="Accountant",
        )
        role_id = role.id
        self.company.delete(hard=True)
        self.assertFalse(Role.all_objects.filter(id=role_id).exists())
