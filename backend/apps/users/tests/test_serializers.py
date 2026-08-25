from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.users.serializers import UserSerializer

User = get_user_model()


class UserSerializerTestCase(TestCase):
    """
    Test suite for UserSerializer formatting and security boundaries.
    """

    def setUp(self):
        self.user = User.objects.create_user(
            email="designer@example.com",
            name="Alex Designer",
            password="StrongPassword123!",
        )

    def test_serializer_contains_expected_camel_case_fields(self):
        """
        Test that serialized output conforms to camelCase convention.
        """
        serializer = UserSerializer(instance=self.user)
        data = serializer.data

        expected_fields = {
            "id",
            "email",
            "name",
            "status",
            "isActive",
            "isStaff",
            "createdAt",
            "updatedAt",
        }
        self.assertEqual(set(data.keys()), expected_fields)
        self.assertEqual(data["id"], str(self.user.id))
        self.assertEqual(data["email"], "designer@example.com")
        self.assertEqual(data["name"], "Alex Designer")
        self.assertEqual(data["status"], "active")
        self.assertTrue(data["isActive"])
        self.assertFalse(data["isStaff"])
        self.assertIsNotNone(data["createdAt"])
        self.assertIsNotNone(data["updatedAt"])

    def test_serializer_never_exposes_password_or_sensitive_fields(self):
        """
        Verify that password, groups, permissions, and internal fields are never exposed.
        """
        serializer = UserSerializer(instance=self.user)
        data = serializer.data

        forbidden_fields = [
            "password",
            "password_hash",
            "groups",
            "user_permissions",
            "deleted_at",
            "is_superuser",
            "is_active",
            "is_staff",
            "created_at",
            "updated_at",
        ]
        for field in forbidden_fields:
            self.assertNotIn(
                field,
                data,
                msg=f"Sensitive or non-camelCase field '{field}' leaked into UserSerializer output",
            )
