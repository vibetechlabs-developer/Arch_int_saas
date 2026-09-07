from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import exceptions as drf_exceptions

from apps.audit.models import AuditLog
from apps.company.models import Company, CompanyStatus
from apps.users.models import CompanyMembership, CompanyMembershipStatus, Role
from apps.users.permission_catalog import ALL_PERMISSION_CODES, DEFAULT_ROLE_PERMISSIONS
from apps.users.services import PermissionService, RoleService

User = get_user_model()


class RoleAssignPermissionsTestCase(TestCase):
    """
    Unit tests for RoleService.assign_permissions (BE-049/BE-051).
    """

    def setUp(self):
        self.company = Company.objects.create(name="Alpha Corp", status=CompanyStatus.ACTIVE)
        self.role = RoleService.create_role(company_id=self.company.id, name="Custom Role")

    def test_assign_permissions_grants_codes(self):
        role = RoleService.assign_permissions(
            role_id=self.role.id, codes=["project.view", "project.edit"]
        )
        self.assertEqual(
            PermissionService.get_permission_codes_for_membership(
                CompanyMembership(role=role, status=CompanyMembershipStatus.ACTIVE)
            ),
            {"project.view", "project.edit"},
        )

    def test_assign_permissions_replaces_previous_set(self):
        RoleService.assign_permissions(role_id=self.role.id, codes=["project.view"])
        RoleService.assign_permissions(role_id=self.role.id, codes=["client.view"])

        from apps.users.repositories import PermissionRepository

        self.assertEqual(PermissionRepository.codes_for_role(self.role.id), {"client.view"})

    def test_assign_permissions_unknown_code_raises_validation_error(self):
        with self.assertRaises(drf_exceptions.ValidationError):
            RoleService.assign_permissions(role_id=self.role.id, codes=["not.a.real.code"])

    def test_assign_permissions_writes_audit_log(self):
        RoleService.assign_permissions(role_id=self.role.id, codes=["project.view"])
        entry = AuditLog.objects.get(
            entity_type="role_permission", entity_id=self.role.id, action="update"
        )
        self.assertEqual(entry.after_state["permission_codes"], ["project.view"])

    def test_assign_permissions_empty_list_clears_all(self):
        RoleService.assign_permissions(role_id=self.role.id, codes=["project.view"])
        RoleService.assign_permissions(role_id=self.role.id, codes=[])

        from apps.users.repositories import PermissionRepository

        self.assertEqual(PermissionRepository.codes_for_role(self.role.id), set())


class PermissionServiceTestCase(TestCase):
    """
    Unit tests for RBAC resolution (BE-051) -- fail-closed behavior for a
    membership with no role, an inactive/revoked membership, or None.
    """

    def setUp(self):
        self.company = Company.objects.create(name="Alpha Corp", status=CompanyStatus.ACTIVE)
        self.user = User.objects.create_user(
            email="member@example.com", name="Member", password="StrongPassword123!"
        )
        self.role = RoleService.create_role(company_id=self.company.id, name="Accountant")
        RoleService.assign_permissions(role_id=self.role.id, codes=["invoice.view"])

    def test_no_membership_has_no_permissions(self):
        self.assertEqual(PermissionService.get_permission_codes_for_membership(None), set())
        self.assertFalse(PermissionService.has_permission(None, "invoice.view"))

    def test_membership_with_no_role_has_no_permissions(self):
        membership = CompanyMembership.objects.create(company=self.company, user=self.user)
        self.assertEqual(PermissionService.get_permission_codes_for_membership(membership), set())

    def test_revoked_membership_has_no_permissions_even_with_role(self):
        membership = CompanyMembership.objects.create(
            company=self.company,
            user=self.user,
            role=self.role,
            status=CompanyMembershipStatus.REVOKED,
        )
        self.assertEqual(PermissionService.get_permission_codes_for_membership(membership), set())

    def test_active_membership_with_role_resolves_its_codes(self):
        membership = CompanyMembership.objects.create(
            company=self.company,
            user=self.user,
            role=self.role,
            status=CompanyMembershipStatus.ACTIVE,
        )
        self.assertTrue(PermissionService.has_permission(membership, "invoice.view"))
        self.assertFalse(PermissionService.has_permission(membership, "invoice.delete"))


class SeedDefaultRolesForCompanyTestCase(TestCase):
    """
    Unit tests for RoleService.seed_default_roles_for_company (BE-049,
    auto-seed-on-company-creation decision).
    """

    def setUp(self):
        self.company = Company.objects.create(name="Alpha Corp", status=CompanyStatus.ACTIVE)

    def test_seeds_every_default_role(self):
        roles = RoleService.seed_default_roles_for_company(self.company)
        self.assertEqual(len(roles), len(DEFAULT_ROLE_PERMISSIONS))
        seeded_names = set(Role.objects.filter(company=self.company).values_list("name", flat=True))
        self.assertEqual(seeded_names, set(DEFAULT_ROLE_PERMISSIONS.keys()))

    def test_owner_role_gets_every_permission_code(self):
        RoleService.seed_default_roles_for_company(self.company)
        owner_role = Role.objects.get(company=self.company, name="Owner")

        from apps.users.repositories import PermissionRepository

        self.assertEqual(PermissionRepository.codes_for_role(owner_role.id), set(ALL_PERMISSION_CODES))

    def test_accountant_role_gets_financial_access(self):
        RoleService.seed_default_roles_for_company(self.company)
        accountant_role = Role.objects.get(company=self.company, name="Accountant / Finance")

        from apps.users.repositories import PermissionRepository

        codes = PermissionRepository.codes_for_role(accountant_role.id)
        self.assertIn("report.financial_access", codes)
        self.assertIn("invoice.delete", codes)

    def test_sales_role_cannot_approve_quotations(self):
        RoleService.seed_default_roles_for_company(self.company)
        sales_role = Role.objects.get(company=self.company, name="Sales / CRM User")

        from apps.users.repositories import PermissionRepository

        codes = PermissionRepository.codes_for_role(sales_role.id)
        self.assertNotIn("quotation.approve", codes)
        self.assertNotIn("report.financial_access", codes)
