import uuid
from django.test import TestCase
from rest_framework.exceptions import ValidationError

from apps.company.models import Company, CompanyStatus
from apps.users.models import Role
from apps.users.serializers import (
    RoleCreateSerializer,
    RoleSerializer,
    RoleUpdateSerializer,
)


class RoleSerializerTestCase(TestCase):
    """
    Unit test suite for Role serializers (BE-014).
    """

    def setUp(self):
        self.company = Company.objects.create(
            name="Design Matrix",
            status=CompanyStatus.ACTIVE,
        )
        self.role = Role.objects.create(
            company=self.company,
            name="Senior Architect",
            description="Designs architectural solutions",
            is_active=True,
        )

    def test_role_serializer_output_camel_case_fields(self):
        """
        Verify RoleSerializer produces standard camelCase JSON representation.
        """
        serializer = RoleSerializer(self.role)
        data = serializer.data

        self.assertEqual(data["id"], str(self.role.id))
        self.assertEqual(data["name"], "Senior Architect")
        self.assertEqual(data["description"], "Designs architectural solutions")
        self.assertEqual(data["companyId"], str(self.company.id))
        self.assertEqual(data["companyName"], "Design Matrix")
        self.assertTrue(data["isActive"])
        self.assertIn("createdAt", data)
        self.assertIn("updatedAt", data)

    def test_role_create_serializer_validation(self):
        """
        Verify RoleCreateSerializer validation rules (blank name rejection, stripping).
        """
        # Valid payload
        valid_data = {
            "name": "  Project Coordinator  ",
            "description": "Coordinates site activities",
            "isActive": True,
            "companyId": str(self.company.id),
        }
        serializer = RoleCreateSerializer(data=valid_data)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertEqual(serializer.validated_data["name"], "Project Coordinator")

        # Blank name
        blank_data = {"name": "   "}
        serializer = RoleCreateSerializer(data=blank_data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("name", serializer.errors)

    def test_role_update_serializer_validation(self):
        """
        Verify RoleUpdateSerializer validation rules for partial updates.
        """
        # Valid partial update
        valid_data = {
            "name": "Lead Project Coordinator",
            "isActive": False,
        }
        serializer = RoleUpdateSerializer(data=valid_data, partial=True)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertEqual(serializer.validated_data["name"], "Lead Project Coordinator")
        self.assertFalse(serializer.validated_data["is_active"])

        # Blank name rejected on update
        blank_data = {"name": "  "}
        serializer = RoleUpdateSerializer(data=blank_data, partial=True)
        self.assertFalse(serializer.is_valid())
        self.assertIn("name", serializer.errors)
