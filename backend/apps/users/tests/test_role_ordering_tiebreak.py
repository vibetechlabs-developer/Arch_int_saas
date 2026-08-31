from django.test import TestCase

from apps.company.models import Company, CompanyStatus
from apps.users.models import Role
from apps.users.selectors import list_roles


class RoleOrderingTieBreakTestCase(TestCase):
    """
    Regression test for BE-030's stabilization pass — see
    apps.clients.tests.test_ordering_tiebreak for the full rationale.
    Role shares the exact same order_by(order_field)-with-no-tie-breaker
    pattern list_clients/list_projects had.
    """

    def test_ordering_is_deterministic_when_created_at_ties(self):
        company = Company.objects.create(name="Alpha Corp", status=CompanyStatus.ACTIVE)
        role_a = Role.objects.create(company=company, name="Role A")
        role_b = Role.objects.create(company=company, name="Role B")

        tied_timestamp = role_a.created_at
        Role.objects.filter(id__in=[role_a.id, role_b.id]).update(created_at=tied_timestamp)

        first_call = list(list_roles(company_id=company.id))
        second_call = list(list_roles(company_id=company.id))

        self.assertEqual(first_call, second_call)
        self.assertEqual({r.id for r in first_call}, {role_a.id, role_b.id})
