from django.test import TestCase

from apps.company.models import Company, CompanyStatus
from apps.company.selectors import list_companies


class CompanyOrderingTieBreakTestCase(TestCase):
    """
    Regression test for BE-030's stabilization pass — see
    apps.clients.tests.test_ordering_tiebreak for the full rationale.
    Company shares the exact same order_by(order_field)-with-no-tie-breaker
    pattern list_clients/list_roles/list_projects had.
    """

    def test_ordering_is_deterministic_when_created_at_ties(self):
        company_a = Company.objects.create(name="Alpha Corp", status=CompanyStatus.ACTIVE)
        company_b = Company.objects.create(name="Beta Corp", status=CompanyStatus.ACTIVE)

        tied_timestamp = company_a.created_at
        Company.objects.filter(id__in=[company_a.id, company_b.id]).update(
            created_at=tied_timestamp
        )

        first_call = list(list_companies())
        second_call = list(list_companies())

        self.assertEqual(first_call, second_call)
        self.assertIn(company_a.id, {c.id for c in first_call})
        self.assertIn(company_b.id, {c.id for c in first_call})
