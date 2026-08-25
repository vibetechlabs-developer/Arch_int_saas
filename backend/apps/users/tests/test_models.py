import uuid
from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.test import TestCase
from django.utils import timezone

User = get_user_model()


class UserModelTestCase(TestCase):
    """
    Test suite for the custom User model and UserManager.
    """

    def setUp(self):
        self.user_email = "architect@example.com"
        self.user_name = "Sarah Architect"
        self.user_password = "SecurePassword123!"

    def test_create_user_successful(self):
        """
        Test creating a standard user with email, name, and password.
        """
        user = User.objects.create_user(
            email=self.user_email,
            name=self.user_name,
            password=self.user_password,
        )

        self.assertIsInstance(user.id, uuid.UUID)
        self.assertEqual(user.email, self.user_email)
        self.assertEqual(user.name, self.user_name)
        self.assertTrue(user.is_active)
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
        self.assertTrue(user.check_password(self.user_password))
        self.assertNotEqual(user.password, self.user_password)
        self.assertIsNotNone(user.created_at)
        self.assertIsNotNone(user.updated_at)
        self.assertIsNone(user.deleted_at)
        self.assertFalse(user.is_deleted)
        self.assertEqual(user.status, "active")

    def test_create_user_normalizes_email(self):
        """
        Test that email addresses are normalized (domain part lowercased).
        """
        user = User.objects.create_user(
            email="Designer@EXAMPLE.COM",
            name="John Designer",
            password=self.user_password,
        )
        self.assertEqual(user.email, "Designer@example.com")

    def test_create_user_without_email_raises_error(self):
        """
        Test that creating a user without an email raises ValueError.
        """
        with self.assertRaises(ValueError) as ctx:
            User.objects.create_user(
                email="",
                name=self.user_name,
                password=self.user_password,
            )
        self.assertIn("Email", str(ctx.exception))

    def test_create_user_without_password(self):
        """
        Test creating a user without password sets unusable password.
        """
        user = User.objects.create_user(
            email="nopass@example.com",
            name="No Pass User",
        )
        self.assertFalse(user.has_usable_password())

    def test_duplicate_email_raises_integrity_error(self):
        """
        Test that creating two users with the same email raises IntegrityError.
        """
        User.objects.create_user(
            email=self.user_email,
            name=self.user_name,
            password=self.user_password,
        )
        with self.assertRaises(IntegrityError):
            User.objects.create_user(
                email=self.user_email,
                name="Duplicate User",
                password="AnotherPassword123!",
            )

    def test_create_superuser_successful(self):
        """
        Test creating a superuser with full administrative privileges.
        """
        superuser = User.objects.create_superuser(
            email="admin@example.com",
            name="Super Admin",
            password="AdminPassword123!",
        )

        self.assertTrue(superuser.is_active)
        self.assertTrue(superuser.is_staff)
        self.assertTrue(superuser.is_superuser)
        self.assertTrue(superuser.check_password("AdminPassword123!"))
        self.assertEqual(superuser.status, "active")

    def test_create_superuser_validation(self):
        """
        Test superuser creation constraints.
        """
        with self.assertRaises(ValueError) as ctx:
            User.objects.create_superuser(
                email="admin2@example.com",
                name="Admin",
                password="pass",
                is_staff=False,
            )
        self.assertIn("is_staff", str(ctx.exception))

        with self.assertRaises(ValueError) as ctx:
            User.objects.create_superuser(
                email="admin3@example.com",
                name="Admin",
                password="pass",
                is_superuser=False,
            )
        self.assertIn("is_superuser", str(ctx.exception))

        with self.assertRaises(ValueError) as ctx:
            User.objects.create_superuser(
                email="admin4@example.com",
                name="Admin",
                password=None,
            )
        self.assertIn("password", str(ctx.exception))

    def test_user_soft_delete_lifecycle(self):
        """
        Test soft deletion, query exclusion, restore, and hard deletion.
        """
        user = User.objects.create_user(
            email="softdelete@example.com",
            name="Soft Delete User",
            password=self.user_password,
        )

        user_id = user.id
        self.assertEqual(User.objects.filter(id=user_id).count(), 1)

        # Soft delete
        user.delete()
        user.refresh_from_db()

        self.assertTrue(user.is_deleted)
        self.assertIsNotNone(user.deleted_at)
        self.assertEqual(user.status, "deleted")

        # Excluded from default manager
        self.assertEqual(User.objects.filter(id=user_id).count(), 0)

        # Present in all_objects and deleted_objects
        self.assertEqual(User.all_objects.filter(id=user_id).count(), 1)
        self.assertEqual(User.deleted_objects.filter(id=user_id).count(), 1)

        # Restore
        user.restore()
        user.refresh_from_db()

        self.assertFalse(user.is_deleted)
        self.assertIsNone(user.deleted_at)
        self.assertEqual(user.status, "active")
        self.assertEqual(User.objects.filter(id=user_id).count(), 1)

        # Hard delete
        user.hard_delete()
        self.assertEqual(User.all_objects.filter(id=user_id).count(), 0)

    def test_user_str_representation(self):
        """
        Test string representation of User model.
        """
        user = User.objects.create_user(
            email="lead@example.com",
            name="Lead Architect",
            password=self.user_password,
        )
        self.assertEqual(str(user), "lead@example.com (Lead Architect)")

    def test_user_inactive_status_property(self):
        """
        Test status property returns 'inactive' when is_active is False.
        """
        user = User.objects.create_user(
            email="inactive@example.com",
            name="Inactive User",
            password=self.user_password,
            is_active=False,
        )
        self.assertEqual(user.status, "inactive")
