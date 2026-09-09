from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase
from rest_framework import exceptions as drf_exceptions, status
from rest_framework.test import APIClient

from apps.audit.models import AuditLog
from apps.authentication.tokens import CompanyUserAccessToken
from apps.common.exceptions import ConflictError
from apps.common.test_utils import make_full_access_membership, make_full_access_role
from apps.company.models import Company, CompanyStatus
from apps.users.models import CompanyMembership, CompanyMembershipStatus, Role
from apps.users.services import CompanyMembershipService

User = get_user_model()


class AddUserServiceTestCase(TestCase):
    """
    Unit tests for CompanyMembershipService.add_user — the genuine
    new-user onboarding flow (distinct from invite_member, which only
    ever links an existing account and 404s on an unknown email).
    """

    def setUp(self):
        self.company1 = Company.objects.create(name="Studio One", status=CompanyStatus.ACTIVE)
        self.company2 = Company.objects.create(name="Studio Two", status=CompanyStatus.ACTIVE)
        self.role1 = Role.objects.create(company=self.company1, name="Accountant", is_active=True)
        self.role2 = Role.objects.create(company=self.company2, name="Sales", is_active=True)

    def test_adds_a_brand_new_user(self):
        membership, user_created, activation_required = CompanyMembershipService.add_user(
            company_id=self.company1.id,
            email="new.person@example.com",
            name="New Person",
            role_id=self.role1.id,
        )

        self.assertTrue(user_created)
        self.assertTrue(activation_required)
        self.assertEqual(membership.company_id, self.company1.id)
        self.assertEqual(membership.role_id, self.role1.id)
        self.assertEqual(membership.status, CompanyMembershipStatus.ACTIVE)

        created_user = User.objects.get(email="new.person@example.com")
        self.assertEqual(created_user.name, "New Person")
        self.assertFalse(created_user.has_usable_password())
        self.assertEqual(mail.outbox[-1].to, ["new.person@example.com"])
        self.assertIn("set your password", mail.outbox[-1].subject.lower())

    def test_links_an_existing_user_without_duplicating_it(self):
        existing = User.objects.create_user(
            email="existing@example.com", name="Existing Person", password="StrongPassword123!"
        )

        membership, user_created, activation_required = CompanyMembershipService.add_user(
            company_id=self.company1.id, email="existing@example.com", name="Ignored Name", role_id=self.role1.id
        )

        self.assertFalse(user_created)
        self.assertFalse(activation_required)
        self.assertEqual(User.objects.filter(email__iexact="existing@example.com").count(), 1)
        self.assertEqual(membership.user_id, existing.id)
        # The existing user's own name is preserved, not overwritten by
        # whatever the admin typed on the Add User form.
        existing.refresh_from_db()
        self.assertEqual(existing.name, "Existing Person")

    def test_existing_user_with_unusable_password_still_gets_activation_email(self):
        User.objects.create_user(email="pending@example.com", name="Pending Person", password=None)

        _, user_created, activation_required = CompanyMembershipService.add_user(
            company_id=self.company1.id, email="pending@example.com", name="Pending Person", role_id=self.role1.id
        )

        self.assertFalse(user_created)
        self.assertTrue(activation_required)
        self.assertEqual(mail.outbox[-1].to, ["pending@example.com"])

    def test_duplicate_active_membership_returns_409(self):
        user = User.objects.create_user(email="dupe@example.com", name="Dupe", password="StrongPassword123!")
        CompanyMembership.objects.create(company=self.company1, user=user, status=CompanyMembershipStatus.ACTIVE)

        with self.assertRaises(ConflictError):
            CompanyMembershipService.add_user(
                company_id=self.company1.id, email="dupe@example.com", name="Dupe", role_id=self.role1.id
            )

    def test_duplicate_invited_membership_returns_409(self):
        user = User.objects.create_user(email="dupe2@example.com", name="Dupe Two", password="StrongPassword123!")
        CompanyMembership.objects.create(company=self.company1, user=user, status=CompanyMembershipStatus.INVITED)

        with self.assertRaises(ConflictError):
            CompanyMembershipService.add_user(
                company_id=self.company1.id, email="dupe2@example.com", name="Dupe Two", role_id=self.role1.id
            )

    def test_revoked_membership_is_reactivated_not_blocked(self):
        user = User.objects.create_user(email="revoked@example.com", name="Revoked", password="StrongPassword123!")
        original_membership = CompanyMembership.objects.create(
            company=self.company1, user=user, role=self.role2, status=CompanyMembershipStatus.REVOKED
        )

        membership, user_created, _ = CompanyMembershipService.add_user(
            company_id=self.company1.id, email="revoked@example.com", name="Revoked", role_id=self.role1.id
        )

        self.assertFalse(user_created)
        self.assertEqual(membership.id, original_membership.id)
        self.assertEqual(membership.status, CompanyMembershipStatus.ACTIVE)
        self.assertEqual(membership.role_id, self.role1.id)
        self.assertEqual(CompanyMembership.objects.filter(company=self.company1, user=user).count(), 1)

    def test_cross_tenant_role_rejected(self):
        with self.assertRaises(drf_exceptions.ValidationError):
            CompanyMembershipService.add_user(
                company_id=self.company1.id, email="x@example.com", name="X", role_id=self.role2.id
            )

    def test_inactive_role_rejected(self):
        self.role1.is_active = False
        self.role1.save()
        with self.assertRaises(drf_exceptions.ValidationError):
            CompanyMembershipService.add_user(
                company_id=self.company1.id, email="x@example.com", name="X", role_id=self.role1.id
            )

    def test_missing_role_id_rejected(self):
        with self.assertRaises(drf_exceptions.ValidationError):
            CompanyMembershipService.add_user(
                company_id=self.company1.id, email="x@example.com", name="X", role_id=None
            )

    def test_blank_name_rejected(self):
        with self.assertRaises(drf_exceptions.ValidationError):
            CompanyMembershipService.add_user(
                company_id=self.company1.id, email="x@example.com", name="   ", role_id=self.role1.id
            )

    def test_multi_company_membership_for_same_user(self):
        CompanyMembershipService.add_user(
            company_id=self.company1.id, email="multi@example.com", name="Multi", role_id=self.role1.id
        )
        user = User.objects.get(email="multi@example.com")

        membership2, user_created2, _ = CompanyMembershipService.add_user(
            company_id=self.company2.id, email="multi@example.com", name="Multi", role_id=self.role2.id
        )

        self.assertFalse(user_created2)
        self.assertEqual(User.objects.filter(email__iexact="multi@example.com").count(), 1)
        self.assertEqual(CompanyMembership.objects.filter(user=user).count(), 2)
        self.assertEqual(membership2.company_id, self.company2.id)

    def test_privilege_escalation_blocked_for_non_admin_actor(self):
        full_role = make_full_access_role(self.company1)
        limited_role = Role.objects.create(company=self.company1, name="Limited", is_active=True)
        actor_user = User.objects.create_user(email="actor@example.com", name="Actor", password="StrongPassword123!")
        actor_membership = CompanyMembership.objects.create(
            company=self.company1, user=actor_user, role=limited_role, status=CompanyMembershipStatus.ACTIVE
        )

        with self.assertRaises(drf_exceptions.PermissionDenied):
            CompanyMembershipService.add_user(
                company_id=self.company1.id,
                email="escalatee@example.com",
                name="Escalatee",
                role_id=full_role.id,
                actor_membership=actor_membership,
            )
        self.assertFalse(User.objects.filter(email="escalatee@example.com").exists())

    def test_membership_creation_failure_rolls_back_the_newly_created_user(self):
        with patch(
            "apps.users.repositories.CompanyMembershipRepository.create", side_effect=RuntimeError("boom")
        ):
            with self.assertRaises(RuntimeError):
                CompanyMembershipService.add_user(
                    company_id=self.company1.id,
                    email="rollback@example.com",
                    name="Rollback",
                    role_id=self.role1.id,
                )

        self.assertFalse(User.objects.filter(email="rollback@example.com").exists())

    def test_audit_log_records_user_created_flag_and_no_secrets(self):
        membership, _, _ = CompanyMembershipService.add_user(
            company_id=self.company1.id, email="audited@example.com", name="Audited", role_id=self.role1.id
        )

        entry = AuditLog.objects.get(entity_type="company_membership", entity_id=membership.id)
        self.assertTrue(entry.after_state["user_created"])
        self.assertEqual(entry.after_state["status"], CompanyMembershipStatus.ACTIVE)
        serialized = str(entry.after_state)
        self.assertNotIn("password", serialized.lower())
        self.assertNotIn("token", serialized.lower())

    def test_new_user_completes_full_authentication_lifecycle(self):
        """
        End-to-end proof (Phase 23/32): the activation email's token is a
        real, usable PasswordResetToken — the exact same one
        /auth/reset-password already consumes — so the new user has a
        genuine path from "just added" to "logged in".
        """
        CompanyMembershipService.add_user(
            company_id=self.company1.id, email="lifecycle@example.com", name="Lifecycle", role_id=self.role1.id
        )
        user = User.objects.get(email="lifecycle@example.com")
        self.assertFalse(user.has_usable_password())

        sent_email = mail.outbox[-1]
        raw_token = sent_email.body.split("token=")[1].split()[0]

        client = APIClient()
        reset_response = client.post(
            "/auth/reset-password",
            {"token": raw_token, "newPassword": "BrandNewPassword123!"},
            format="json",
        )
        self.assertEqual(reset_response.status_code, status.HTTP_200_OK)

        user.refresh_from_db()
        self.assertTrue(user.has_usable_password())

        login_response = client.post(
            "/auth/login",
            {"email": "lifecycle@example.com", "password": "BrandNewPassword123!"},
            format="json",
        )
        self.assertEqual(login_response.status_code, status.HTTP_200_OK)
        login_data = login_response.json()["data"]
        self.assertIn("accessToken", login_data)

        client.credentials(HTTP_AUTHORIZATION=f"Bearer {login_data['accessToken']}")
        memberships_response = client.get("/auth/memberships")
        self.assertEqual(memberships_response.status_code, status.HTTP_200_OK)
        companies = [m["companyName"] for m in memberships_response.json()["data"]]
        self.assertIn("Studio One", companies)


class AddUserViewTestCase(TestCase):
    """
    Integration tests for POST /company-memberships/add-user.
    """

    def setUp(self):
        self.client = APIClient(SERVER_NAME="localhost")
        self.company1 = Company.objects.create(name="Studio One", status=CompanyStatus.ACTIVE)
        self.company2 = Company.objects.create(name="Studio Two", status=CompanyStatus.ACTIVE)
        self.role1 = Role.objects.create(company=self.company1, name="Accountant", is_active=True)
        self.role2 = Role.objects.create(company=self.company2, name="Sales", is_active=True)

        self.admin_user = User.objects.create_user(
            email="admin@company1.com", name="Admin User", password="StrongPassword123!"
        )
        make_full_access_membership(self.company1, self.admin_user)
        self.admin_token = str(CompanyUserAccessToken.for_user(self.admin_user))

        self.limited_role = Role.objects.create(company=self.company1, name="Limited", is_active=True)
        self.limited_user = User.objects.create_user(
            email="limited@company1.com", name="Limited User", password="StrongPassword123!"
        )
        CompanyMembership.objects.create(
            company=self.company1, user=self.limited_user, role=self.limited_role, status=CompanyMembershipStatus.ACTIVE
        )
        self.limited_token = str(CompanyUserAccessToken.for_user(self.limited_user))

    def test_unauthenticated_returns_401(self):
        response = self.client.post("/company-memberships/add-user", {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_missing_permission_returns_403(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.limited_token}")
        response = self.client.post(
            "/company-memberships/add-user",
            {"email": "new@example.com", "name": "New Person", "roleId": str(self.role1.id)},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_successful_add_user_response_shape_has_no_secrets(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.admin_token}")
        response = self.client.post(
            "/company-memberships/add-user",
            {"email": "brandnew@example.com", "name": "Brand New", "roleId": str(self.role1.id)},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        data = response.json()["data"]
        self.assertTrue(data["userCreated"])
        self.assertTrue(data["activationRequired"])
        self.assertEqual(data["membership"]["status"], "active")
        self.assertEqual(data["membership"]["userEmail"], "brandnew@example.com")
        raw_body = response.content.decode().lower()
        self.assertNotIn("password", raw_body)
        self.assertNotIn("token", raw_body)

    def test_new_user_immediately_visible_in_members_list(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.admin_token}")
        self.client.post(
            "/company-memberships/add-user",
            {"email": "visible@example.com", "name": "Visible Person", "roleId": str(self.role1.id)},
            format="json",
        )

        list_response = self.client.get("/company-memberships")
        emails = [m["userEmail"] for m in list_response.json()["data"]]
        self.assertIn("visible@example.com", emails)

    def test_cross_tenant_role_returns_400_not_404(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.admin_token}")
        response = self.client.post(
            "/company-memberships/add-user",
            {"email": "x@example.com", "name": "X", "roleId": str(self.role2.id)},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_nonexistent_role_returns_404(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.admin_token}")
        response = self.client.post(
            "/company-memberships/add-user",
            {"email": "x@example.com", "name": "X", "roleId": "00000000-0000-0000-0000-000000000000"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_duplicate_membership_returns_409(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.admin_token}")
        self.client.post(
            "/company-memberships/add-user",
            {"email": "dupe@example.com", "name": "Dupe", "roleId": str(self.role1.id)},
            format="json",
        )
        response = self.client.post(
            "/company-memberships/add-user",
            {"email": "dupe@example.com", "name": "Dupe", "roleId": str(self.role1.id)},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)

    def test_missing_fields_return_400(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.admin_token}")
        response = self.client.post("/company-memberships/add-user", {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class SelfActionSafetyTestCase(TestCase):
    """
    BE-054-adjacent safety guard added alongside Add User (Phase 28):
    nothing previously stopped an admin from suspending or removing their
    own membership. Last-owner protection is a deliberate non-goal here —
    Role has no system_key/protected-role identity (BE-069), so any
    "who is the owner" check would have to match on the free-text display
    name, exactly the fragile pattern this codebase has already flagged
    as technical debt rather than a pattern to extend.
    """

    def setUp(self):
        self.client = APIClient(SERVER_NAME="localhost")
        self.company = Company.objects.create(name="Studio One", status=CompanyStatus.ACTIVE)
        self.admin_user = User.objects.create_user(
            email="admin@company1.com", name="Admin User", password="StrongPassword123!"
        )
        self.membership = make_full_access_membership(self.company, self.admin_user)
        self.admin_token = str(CompanyUserAccessToken.for_user(self.admin_user))

    def test_admin_cannot_suspend_self(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.admin_token}")
        response = self.client.post(f"/company-memberships/{self.membership.id}/suspend")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.membership.refresh_from_db()
        self.assertEqual(self.membership.status, CompanyMembershipStatus.ACTIVE)

    def test_admin_cannot_remove_self(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.admin_token}")
        response = self.client.delete(f"/company-memberships/{self.membership.id}")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertTrue(CompanyMembership.objects.filter(id=self.membership.id).exists())

    def test_admin_can_still_suspend_someone_else(self):
        other_user = User.objects.create_user(
            email="other@company1.com", name="Other User", password="StrongPassword123!"
        )
        other_membership = CompanyMembership.objects.create(
            company=self.company, user=other_user, status=CompanyMembershipStatus.ACTIVE
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.admin_token}")
        response = self.client.post(f"/company-memberships/{other_membership.id}/suspend")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
