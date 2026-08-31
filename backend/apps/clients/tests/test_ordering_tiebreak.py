from django.test import TestCase

from apps.clients.models import Client
from apps.clients.selectors import list_clients
from apps.company.models import Company, CompanyStatus


class ClientOrderingTieBreakTestCase(TestCase):
    """
    Regression test for BE-030's stabilization pass: list_clients's
    default -created_at ordering had no secondary tie-breaker (the same
    bug class found and fixed in apps.projects during BE-028). Forces two
    rows to share an identical created_at (bypassing auto_now_add via a
    direct .update(), since the normal create path can't reliably
    reproduce the OS-clock-resolution collision that surfaced the bug) to
    prove the ordering no longer depends on undefined tie behavior.
    """

    def test_ordering_is_deterministic_when_created_at_ties(self):
        company = Company.objects.create(name="Alpha Corp", status=CompanyStatus.ACTIVE)
        client_a = Client.objects.create(company=company, name="Client A")
        client_b = Client.objects.create(company=company, name="Client B")

        tied_timestamp = client_a.created_at
        Client.objects.filter(id__in=[client_a.id, client_b.id]).update(created_at=tied_timestamp)

        first_call = list(list_clients(company_id=company.id))
        second_call = list(list_clients(company_id=company.id))

        self.assertEqual(first_call, second_call)
        self.assertEqual({c.id for c in first_call}, {client_a.id, client_b.id})
