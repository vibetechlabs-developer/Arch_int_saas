import uuid
from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.test import TestCase

from apps.company.models import Company, CompanyStatus
from apps.users.models import CompanyMembership, CompanyMembershipStatus
from apps.users.serializers import CompanyMembershipSerializer

User = get_user_model()


class CompanyMembershipTestCase(TestCase):
    """
    Unit tests for CompanyMembership model and serialization (BE-011).
    """

    def setUp(self):
        self.user1 = User.objects.create_user(
            email="architect@example.com",
            name="Alice Architect",
            password="StrongPassword123!",
        )
        self.user2 = User.objects.create_user(
            email="designer@example.com",
            name="Bob Designer",
            password="StrongPassword123!",
        )
        self.company1 = Company.objects.create(
            name="Alpha Designs",
            status=CompanyStatus.ACTIVE,
        )
        self.company2 = Company.objects.create(
            name="Beta Studios",
            status=CompanyStatus.ACTIVE,
        )

    def test_create_company_membership_success(self):
        """
        Verify creating a valid CompanyMembership record.
        """
        membership = CompanyMembership.objects.create(
            company=self.company1,
            user=self.user1,
        )

        self.assertIsInstance(membership.id, uuid.UUID)
        self.assertEqual(membership.company, self.company1)
        self.assertEqual(membership.user, self.user1)
        self.assertEqual(membership.status, CompanyMembershipStatus.ACTIVE)
        self.assertIsNotNone(membership.created_at)
        self.assertIsNotNone(membership.updated_at)
        self.assertIsNone(membership.deleted_at)
        self.assertFalse(membership.is_deleted)

    def test_membership_status_choices(self):
        """
        Verify membership status choices (active, invited, revoked).
        """
        membership = CompanyMembership.objects.create(
            company=self.company1,
            user=self.user1,
            status=CompanyMembershipStatus.INVITED,
        )
        self.assertEqual(membership.status, "invited")

        membership.status = CompanyMembershipStatus.ACTIVE
        membership.save()
        membership.refresh_from_db()
        self.assertEqual(membership.status, "active")

        membership.status = CompanyMembershipStatus.REVOKED
        membership.save()
        membership.refresh_from_db()
        self.assertEqual(membership.status, "revoked")

    def test_unique_company_user_membership_constraint(self):
        """
        Verify that a user cannot have multiple active memberships in the same company.
        """
        CompanyMembership.objects.create(
            company=self.company1,
            user=self.user1,
        )

        with self.assertRaises(IntegrityError):
            CompanyMembership.objects.create(
                company=self.company1,
                user=self.user1,
            )

    def test_user_can_belong_to_multiple_companies(self):
        """
        Verify that a single global user identity can hold memberships in multiple companies.
        """
        m1 = CompanyMembership.objects.create(
            company=self.company1,
            user=self.user1,
        )
        m2 = CompanyMembership.objects.create(
            company=self.company2,
            user=self.user1,
        )

        user_memberships = self.user1.memberships.all()
        self.assertEqual(user_memberships.count(), 2)
        self.assertIn(m1, user_memberships)
        self.assertIn(m2, user_memberships)

    def test_company_can_have_multiple_users(self):
        """
        Verify that a single company can have multiple member users.
        """
        m1 = CompanyMembership.objects.create(
            company=self.company1,
            user=self.user1,
        )
        m2 = CompanyMembership.objects.create(
            company=self.company1,
            user=self.user2,
        )

        company_memberships = self.company1.memberships.all()
        self.assertEqual(company_memberships.count(), 2)
        self.assertIn(m1, company_memberships)
        self.assertIn(m2, company_memberships)

    def test_membership_soft_delete_lifecycle(self):
        """
        Verify soft delete, restore, and manager behavior for CompanyMembership.
        """
        membership = CompanyMembership.objects.create(
            company=self.company1,
            user=self.user1,
        )
        m_id = membership.id

        # 1. Soft delete
        membership.delete()
        self.assertTrue(membership.is_deleted)
        self.assertIsNotNone(membership.deleted_at)

        # 2. Excluded from default manager
        self.assertFalse(CompanyMembership.objects.filter(id=m_id).exists())
        self.assertTrue(CompanyMembership.all_objects.filter(id=m_id).exists())
        self.assertTrue(CompanyMembership.deleted_objects.filter(id=m_id).exists())

        # 3. Restore
        membership.restore()
        self.assertFalse(membership.is_deleted)
        self.assertIsNone(membership.deleted_at)
        self.assertTrue(CompanyMembership.objects.filter(id=m_id).exists())

        # 4. Hard delete
        membership.hard_delete()
        self.assertFalse(CompanyMembership.all_objects.filter(id=m_id).exists())

    def test_membership_serializer_camel_case(self):
        """
        Verify CompanyMembershipSerializer output conforming to camelCase standard.
        """
        membership = CompanyMembership.objects.create(
            company=self.company1,
            user=self.user1,
            status=CompanyMembershipStatus.ACTIVE,
        )

        serializer = CompanyMembershipSerializer(membership)
        data = serializer.data

        expected_fields = {
            "id",
            "companyId",
            "companyName",
            "companyStatus",
            "userId",
            "userEmail",
            "userName",
            "status",
            "createdAt",
            "updatedAt",
        }
        self.assertEqual(set(data.keys()), expected_fields)
        self.assertEqual(str(data["id"]), str(membership.id))
        self.assertEqual(str(data["companyId"]), str(self.company1.id))
        self.assertEqual(data["companyName"], "Alpha Designs")
        self.assertEqual(data["companyStatus"], "active")
        self.assertEqual(str(data["userId"]), str(self.user1.id))
        self.assertEqual(data["userEmail"], "architect@example.com")
        self.assertEqual(data["userName"], "Alice Architect")
        self.assertEqual(data["status"], "active")

    def test_cascade_delete_on_hard_delete(self):
        """
        Verify hard deleting a company removes its memberships.
        """
        CompanyMembership.objects.create(
            company=self.company1,
            user=self.user1,
        )
        self.assertEqual(CompanyMembership.all_objects.count(), 1)

        self.company1.hard_delete()
        self.assertEqual(CompanyMembership.all_objects.count(), 0)
