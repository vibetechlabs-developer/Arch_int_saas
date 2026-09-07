from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import exceptions as drf_exceptions

from apps.audit.models import AuditLog
from apps.common.exceptions import ConflictError
from apps.common.test_utils import make_full_access_role
from apps.company.models import Company, CompanyStatus
from apps.users.models import CompanyMembership, CompanyMembershipStatus, Role
from apps.users.services import CompanyMembershipService, RoleService

User = get_user_model()


class CompanyMembershipServiceTestCase(TestCase):
    """
    Unit tests for CompanyMembershipService (BE-052): invite, list, remove,
    suspend, reactivate, assign role -- and the audit trail for each (BE-055).

    BE-054 §1: `role_id` is now a required parameter (no default) on
    `invite_member` -- every call below passes it explicitly, `None`
    where a test doesn't care about role assignment and just needs to
    reach a check that runs before the "role is required" validation
    (unknown email, duplicate membership).
    """

    def setUp(self):
        self.company1 = Company.objects.create(name="Alpha Corp", status=CompanyStatus.ACTIVE)
        self.company2 = Company.objects.create(name="Beta Corp", status=CompanyStatus.ACTIVE)
        self.user = User.objects.create_user(
            email="newmember@example.com", name="New Member", password="StrongPassword123!"
        )
        self.role1 = Role.objects.create(company=self.company1, name="Accountant", is_active=True)
        self.role2 = Role.objects.create(company=self.company2, name="Sales", is_active=True)

    def test_invite_member_creates_invited_membership(self):
        membership = CompanyMembershipService.invite_member(
            company_id=self.company1.id, email=self.user.email, role_id=self.role1.id
        )
        self.assertEqual(membership.company_id, self.company1.id)
        self.assertEqual(membership.user_id, self.user.id)
        self.assertEqual(membership.status, CompanyMembershipStatus.INVITED)
        self.assertEqual(membership.role_id, self.role1.id)

    def test_invite_member_without_role_id_raises_validation_error(self):
        with self.assertRaises(drf_exceptions.ValidationError):
            CompanyMembershipService.invite_member(
                company_id=self.company1.id, email=self.user.email, role_id=None
            )

    def test_invite_member_with_role(self):
        membership = CompanyMembershipService.invite_member(
            company_id=self.company1.id, email=self.user.email, role_id=self.role1.id
        )
        self.assertEqual(membership.role_id, self.role1.id)

    def test_invite_member_with_role_from_other_company_rejected(self):
        with self.assertRaises(drf_exceptions.ValidationError):
            CompanyMembershipService.invite_member(
                company_id=self.company1.id, email=self.user.email, role_id=self.role2.id
            )

    def test_invite_member_with_inactive_role_rejected(self):
        self.role1.is_active = False
        self.role1.save()
        with self.assertRaises(drf_exceptions.ValidationError):
            CompanyMembershipService.invite_member(
                company_id=self.company1.id, email=self.user.email, role_id=self.role1.id
            )

    def test_invite_member_with_soft_deleted_role_raises_not_found(self):
        role_id = self.role1.id
        self.role1.delete()
        with self.assertRaises(drf_exceptions.NotFound):
            CompanyMembershipService.invite_member(
                company_id=self.company1.id, email=self.user.email, role_id=role_id
            )

    def test_invite_member_unknown_email_raises_not_found(self):
        with self.assertRaises(drf_exceptions.NotFound):
            CompanyMembershipService.invite_member(
                company_id=self.company1.id, email="ghost@example.com", role_id=None
            )

    def test_invite_member_already_a_member_raises_conflict(self):
        CompanyMembershipService.invite_member(
            company_id=self.company1.id, email=self.user.email, role_id=self.role1.id
        )
        with self.assertRaises(ConflictError):
            CompanyMembershipService.invite_member(
                company_id=self.company1.id, email=self.user.email, role_id=self.role1.id
            )

    def test_invite_member_writes_audit_log(self):
        membership = CompanyMembershipService.invite_member(
            company_id=self.company1.id, email=self.user.email, role_id=self.role1.id
        )
        entry = AuditLog.objects.get(
            entity_type="company_membership", entity_id=membership.id, action="create"
        )
        self.assertEqual(entry.after_state["status"], "invited")

    def test_invite_member_escalation_guard_rejects_role_beyond_actors_own_codes(self):
        """
        BE-054 §12: a non-platform-admin actor can't invite someone
        directly into a role that grants permission codes the actor
        doesn't hold themselves.
        """
        RoleService.assign_permissions(role_id=self.role1.id, codes=["invoice.view", "invoice.create"])
        low_priv_role = Role.objects.create(company=self.company1, name="Low Priv", is_active=True)
        RoleService.assign_permissions(role_id=low_priv_role.id, codes=["invoice.view"])
        actor = User.objects.create_user(
            email="actor@example.com", name="Actor", password="StrongPassword123!"
        )
        actor_membership = CompanyMembership.objects.create(
            company=self.company1, user=actor, role=low_priv_role, status=CompanyMembershipStatus.ACTIVE
        )

        with self.assertRaises(drf_exceptions.PermissionDenied):
            CompanyMembershipService.invite_member(
                company_id=self.company1.id,
                email=self.user.email,
                role_id=self.role1.id,
                actor_membership=actor_membership,
            )

    def test_invite_member_platform_admin_bypasses_escalation_guard(self):
        """
        actor_membership=None (the platform-admin case) skips the
        escalation check entirely.
        """
        RoleService.assign_permissions(role_id=self.role1.id, codes=["invoice.view", "invoice.create"])
        membership = CompanyMembershipService.invite_member(
            company_id=self.company1.id,
            email=self.user.email,
            role_id=self.role1.id,
            actor_membership=None,
        )
        self.assertEqual(membership.role_id, self.role1.id)

    def test_assign_role(self):
        membership = CompanyMembershipService.invite_member(
            company_id=self.company1.id, email=self.user.email, role_id=self.role1.id
        )
        updated = CompanyMembershipService.assign_role(
            membership_id=membership.id, role_id=self.role1.id
        )
        self.assertEqual(updated.role_id, self.role1.id)

    def test_assign_role_from_other_company_rejected(self):
        membership = CompanyMembershipService.invite_member(
            company_id=self.company1.id, email=self.user.email, role_id=self.role1.id
        )
        with self.assertRaises(drf_exceptions.ValidationError):
            CompanyMembershipService.assign_role(
                membership_id=membership.id, role_id=self.role2.id
            )

    def test_assign_role_inactive_role_rejected(self):
        membership = CompanyMembershipService.invite_member(
            company_id=self.company1.id, email=self.user.email, role_id=self.role1.id
        )
        self.role1.is_active = False
        self.role1.save()
        with self.assertRaises(drf_exceptions.ValidationError):
            CompanyMembershipService.assign_role(membership_id=membership.id, role_id=self.role1.id)

    def test_assign_role_none_clears_role(self):
        membership = CompanyMembershipService.invite_member(
            company_id=self.company1.id, email=self.user.email, role_id=self.role1.id
        )
        updated = CompanyMembershipService.assign_role(membership_id=membership.id, role_id=None)
        self.assertIsNone(updated.role)

    def test_assign_role_escalation_guard_rejects_role_beyond_actors_own_codes(self):
        RoleService.assign_permissions(role_id=self.role1.id, codes=["invoice.view", "invoice.create"])
        low_priv_role = Role.objects.create(company=self.company1, name="Low Priv", is_active=True)
        RoleService.assign_permissions(role_id=low_priv_role.id, codes=["invoice.view"])
        actor = User.objects.create_user(
            email="actor@example.com", name="Actor", password="StrongPassword123!"
        )
        actor_membership = CompanyMembership.objects.create(
            company=self.company1, user=actor, role=low_priv_role, status=CompanyMembershipStatus.ACTIVE
        )
        target_membership = CompanyMembershipService.invite_member(
            company_id=self.company1.id, email=self.user.email, role_id=low_priv_role.id
        )

        with self.assertRaises(drf_exceptions.PermissionDenied):
            CompanyMembershipService.assign_role(
                membership_id=target_membership.id,
                role_id=self.role1.id,
                actor_membership=actor_membership,
            )

    def test_assign_role_self_escalation_via_crafted_role_id_denied(self):
        """
        BE-054 §10/#O: an actor cannot assign themselves (via their own
        membership id) a role more powerful than the one they already
        hold, even though they legitimately hold `user.manage`.
        """
        full_role = make_full_access_role(self.company1)
        low_priv_role = Role.objects.create(company=self.company1, name="Low Priv", is_active=True)
        RoleService.assign_permissions(role_id=low_priv_role.id, codes=["user.manage"])
        actor = User.objects.create_user(
            email="selfescalate@example.com", name="Self Escalate", password="StrongPassword123!"
        )
        actor_membership = CompanyMembership.objects.create(
            company=self.company1, user=actor, role=low_priv_role, status=CompanyMembershipStatus.ACTIVE
        )

        with self.assertRaises(drf_exceptions.PermissionDenied):
            CompanyMembershipService.assign_role(
                membership_id=actor_membership.id,
                role_id=full_role.id,
                actor_membership=actor_membership,
            )
        actor_membership.refresh_from_db()
        self.assertEqual(actor_membership.role_id, low_priv_role.id)

    def test_suspend_then_reactivate(self):
        membership = CompanyMembership.objects.create(
            company=self.company1, user=self.user, status=CompanyMembershipStatus.ACTIVE
        )
        suspended = CompanyMembershipService.suspend_member(membership.id)
        self.assertEqual(suspended.status, CompanyMembershipStatus.REVOKED)

        reactivated = CompanyMembershipService.reactivate_member(membership.id)
        self.assertEqual(reactivated.status, CompanyMembershipStatus.ACTIVE)

    def test_remove_member_soft_deletes(self):
        membership = CompanyMembership.objects.create(company=self.company1, user=self.user)
        m_id = membership.id
        CompanyMembershipService.remove_member(m_id)

        self.assertFalse(CompanyMembership.objects.filter(id=m_id).exists())
        self.assertTrue(CompanyMembership.all_objects.filter(id=m_id).exists())

    def test_remove_member_writes_audit_log(self):
        membership = CompanyMembership.objects.create(company=self.company1, user=self.user)
        CompanyMembershipService.remove_member(membership.id)
        entry = AuditLog.objects.get(
            entity_type="company_membership", entity_id=membership.id, action="delete"
        )
        self.assertEqual(entry.before_state["status"], "active")

    def test_get_membership_scoped_to_wrong_company_raises_not_found(self):
        membership = CompanyMembership.objects.create(company=self.company1, user=self.user)
        with self.assertRaises(drf_exceptions.NotFound):
            CompanyMembershipService.get_membership_by_id(
                membership.id, company_id=self.company2.id
            )

    def test_list_memberships_scoped_to_company(self):
        CompanyMembership.objects.create(company=self.company1, user=self.user)
        other_user = User.objects.create_user(
            email="other@example.com", name="Other", password="StrongPassword123!"
        )
        CompanyMembership.objects.create(company=self.company2, user=other_user)

        results = CompanyMembershipService.list_memberships(company_id=self.company1.id)
        self.assertEqual(results.count(), 1)
        self.assertEqual(results.first().user_id, self.user.id)

    def test_list_my_memberships_returns_only_active_across_companies(self):
        CompanyMembership.objects.create(
            company=self.company1, user=self.user, status=CompanyMembershipStatus.ACTIVE
        )
        CompanyMembership.objects.create(
            company=self.company2, user=self.user, status=CompanyMembershipStatus.REVOKED
        )

        results = CompanyMembershipService.list_my_memberships(self.user.id)
        self.assertEqual(results.count(), 1)
        self.assertEqual(results.first().company_id, self.company1.id)
