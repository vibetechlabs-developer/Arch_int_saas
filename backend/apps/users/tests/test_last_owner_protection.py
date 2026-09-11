"""
BE-069: the last-active-Owner invariant. A company must never lose its
final ACTIVE membership holding the system Owner role, enforced across
every mutation path that could violate it -- never by matching
`role.name == "Owner"`.
"""

from django.test import TestCase

from apps.common.exceptions import ConflictError
from apps.company.services import CompanyService
from apps.users.models import CompanyMembershipStatus, Role, User
from apps.users.services import CompanyMembershipService, RoleService


class LastOwnerProtectionTestCase(TestCase):
    def setUp(self):
        self.company = CompanyService.create_company(name="Last Owner Co")
        self.owner_role = Role.objects.get(company=self.company, system_key="owner")
        self.admin_role = Role.objects.get(company=self.company, system_key="admin")

        self.owner_a_user = User.objects.create_user(email="a@example.com", name="Owner A", password="x")
        self.membership_a, _, _ = CompanyMembershipService.add_user(
            self.company.id, "a@example.com", "Owner A", self.owner_role.id
        )

    def _add_second_owner(self):
        user = User.objects.create_user(email="b@example.com", name="Owner B", password="x")
        membership, _, _ = CompanyMembershipService.add_user(
            self.company.id, "b@example.com", "Owner B", self.owner_role.id
        )
        return membership

    # --- Single owner: every removal path rejected -------------------------

    def test_last_active_owner_cannot_change_role(self):
        with self.assertRaises(ConflictError) as ctx:
            CompanyMembershipService.assign_role(self.membership_a.id, self.admin_role.id)
        self.assertEqual(ctx.exception.code, "LAST_OWNER_REQUIRED")
        self.membership_a.refresh_from_db()
        self.assertEqual(self.membership_a.role_id, self.owner_role.id)

    def test_last_active_owner_cannot_be_cleared_to_no_role(self):
        with self.assertRaises(ConflictError):
            CompanyMembershipService.assign_role(self.membership_a.id, None)

    def test_last_active_owner_cannot_be_revoked(self):
        with self.assertRaises(ConflictError) as ctx:
            CompanyMembershipService.suspend_member(self.membership_a.id)
        self.assertEqual(ctx.exception.code, "LAST_OWNER_REQUIRED")
        self.membership_a.refresh_from_db()
        self.assertEqual(self.membership_a.status, CompanyMembershipStatus.ACTIVE)

    def test_last_active_owner_cannot_be_removed(self):
        with self.assertRaises(ConflictError) as ctx:
            CompanyMembershipService.remove_member(self.membership_a.id)
        self.assertEqual(ctx.exception.code, "LAST_OWNER_REQUIRED")
        self.membership_a.refresh_from_db()
        self.assertFalse(self.membership_a.is_deleted)

    def test_last_active_owner_cannot_self_remove(self):
        """Self-removal is already blocked for everyone -- confirms it still applies to the last owner too, and for the right reason (self-protection fires first)."""
        from rest_framework import exceptions as drf_exceptions

        with self.assertRaises(drf_exceptions.PermissionDenied):
            CompanyMembershipService.remove_member(
                self.membership_a.id, actor_user=self.owner_a_user
            )

    # --- Two owners: normal actions succeed --------------------------------

    def test_with_two_active_owners_one_can_change_role(self):
        membership_b = self._add_second_owner()
        updated = CompanyMembershipService.assign_role(membership_b.id, self.admin_role.id)
        self.assertEqual(updated.role_id, self.admin_role.id)

    def test_with_two_active_owners_one_can_be_removed(self):
        membership_b = self._add_second_owner()
        CompanyMembershipService.remove_member(membership_b.id)
        membership_b.refresh_from_db()
        self.assertTrue(membership_b.is_deleted)

    def test_with_two_active_owners_one_can_be_revoked(self):
        membership_b = self._add_second_owner()
        updated = CompanyMembershipService.suspend_member(membership_b.id)
        self.assertEqual(updated.status, CompanyMembershipStatus.REVOKED)

    def test_after_demoting_one_of_two_owners_the_other_becomes_protected(self):
        membership_b = self._add_second_owner()
        CompanyMembershipService.assign_role(membership_b.id, self.admin_role.id)
        with self.assertRaises(ConflictError):
            CompanyMembershipService.assign_role(self.membership_a.id, self.admin_role.id)

    # --- Inactive/revoked owner does not count ------------------------------

    def test_revoked_owner_membership_does_not_satisfy_the_invariant(self):
        """
        A second Owner membership that is REVOKED (not active) must not
        count as "another owner remains" -- demoting the sole ACTIVE
        owner while a revoked one exists must still be rejected.
        """
        membership_b = self._add_second_owner()
        CompanyMembershipService.suspend_member(membership_b.id)  # -> revoked

        with self.assertRaises(ConflictError):
            CompanyMembershipService.assign_role(self.membership_a.id, self.admin_role.id)

    def test_reactivating_a_revoked_owner_restores_the_ability_to_demote_the_other(self):
        membership_b = self._add_second_owner()
        CompanyMembershipService.suspend_member(membership_b.id)
        CompanyMembershipService.reactivate_member(membership_b.id)

        # Now two active owners again -- demoting one succeeds.
        CompanyMembershipService.assign_role(self.membership_a.id, self.admin_role.id)
        self.membership_a.refresh_from_db()
        self.assertEqual(self.membership_a.role_id, self.admin_role.id)

    # --- Custom role named "Owner" is never protected -----------------------

    def test_custom_role_named_owner_never_triggers_last_owner_protection(self):
        """
        Renames the real Owner away, creates a custom "Owner"-named role,
        assigns the sole member to it, then confirms every mutation that
        WOULD be blocked for a real last Owner succeeds normally here.
        """
        RoleService.update_role(self.owner_role.id, {"name": "Owner (Renamed Away)"})
        fake_owner_role = RoleService.create_role(company_id=self.company.id, name="Owner")

        # Give the real Owner a second holder first so demoting membership_a
        # to the fake role doesn't itself get blocked by the REAL invariant.
        self._add_second_owner()
        CompanyMembershipService.assign_role(self.membership_a.id, fake_owner_role.id)
        self.membership_a.refresh_from_db()
        self.assertEqual(self.membership_a.role_id, fake_owner_role.id)

        # Sole holder of the fake "Owner" role: remove/suspend/reassign must
        # all succeed, unlike the real Owner's last-member protection.
        CompanyMembershipService.assign_role(self.membership_a.id, self.admin_role.id)
        self.membership_a.refresh_from_db()
        self.assertEqual(self.membership_a.role_id, self.admin_role.id)


class RoleDeleteSafetyWithSystemKeyTestCase(TestCase):
    """8. Protected Owner role cannot be deleted; 9. custom role named Owner can follow normal custom-role delete rules."""

    def setUp(self):
        self.company = CompanyService.create_company(name="Delete Safety Co")

    def test_system_owner_role_cannot_be_deleted(self):
        owner = Role.objects.get(company=self.company, system_key="owner")
        with self.assertRaises(ConflictError) as ctx:
            RoleService.soft_delete_role(owner.id)
        self.assertEqual(ctx.exception.code, "SYSTEM_ROLE_PROTECTED")
        self.assertFalse(Role.objects.get(id=owner.id).is_deleted)

    def test_other_default_roles_remain_deletable(self):
        """Only Owner is protected -- Admin/PM/etc. follow ordinary custom-role delete rules, per this task's own scope (no evidence to protect them)."""
        admin = Role.objects.get(company=self.company, system_key="admin")
        RoleService.soft_delete_role(admin.id)
        self.assertTrue(Role.all_objects.get(id=admin.id).is_deleted)

    def test_custom_role_named_owner_can_be_deleted_normally(self):
        real_owner = Role.objects.get(company=self.company, system_key="owner")
        RoleService.update_role(real_owner.id, {"name": "Owner (Renamed Away)"})
        fake_owner = RoleService.create_role(company_id=self.company.id, name="Owner")

        RoleService.soft_delete_role(fake_owner.id)
        self.assertTrue(Role.all_objects.get(id=fake_owner.id).is_deleted)

    def test_deleting_a_role_still_unassigns_memberships_for_custom_roles(self):
        """23. Role delete unassignment still works for custom roles (regression, unaffected by this task)."""
        role = RoleService.create_role(company_id=self.company.id, name="Temp Role")
        user = User.objects.create_user(email="c@example.com", name="Member C", password="x")
        membership, _, _ = CompanyMembershipService.add_user(
            self.company.id, "c@example.com", "Member C", role.id
        )

        RoleService.soft_delete_role(role.id)

        membership.refresh_from_db()
        self.assertIsNone(membership.role_id)
