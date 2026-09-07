import datetime
from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from apps.authentication.tokens import CompanyUserAccessToken
from apps.clients.models import Client
from apps.common.test_utils import make_full_access_membership
from apps.company.models import Company, CompanyStatus
from apps.projects.models import Project, ProjectStatus
from apps.projects.services import ProjectService
from apps.users.models import CompanyMembership, CompanyMembershipStatus

User = get_user_model()


class ProjectListFilterServiceTestCase(TestCase):
    """
    Unit tests for ProjectService.list_projects filtering/ordering (BE-028).
    """

    def setUp(self):
        self.company = Company.objects.create(name="Alpha Corp", status=CompanyStatus.ACTIVE)
        self.client_a = Client.objects.create(company=self.company, name="Client A")
        self.client_b = Client.objects.create(company=self.company, name="Client B")

        self.user_a = User.objects.create_user(
            email="a@company1.com", name="User A", password="StrongPassword123!"
        )
        self.user_b = User.objects.create_user(
            email="b@company1.com", name="User B", password="StrongPassword123!"
        )
        CompanyMembership.objects.create(
            company=self.company, user=self.user_a, status=CompanyMembershipStatus.ACTIVE
        )
        CompanyMembership.objects.create(
            company=self.company, user=self.user_b, status=CompanyMembershipStatus.ACTIVE
        )

        self.project_draft = Project.objects.create(
            company=self.company,
            client=self.client_a,
            name="Draft Project",
            status=ProjectStatus.DRAFT,
            priority="High",
            assigned_to=self.user_a,
            start_date=datetime.date(2026, 1, 1),
            deadline=datetime.date(2026, 3, 1),
        )
        self.project_planning = Project.objects.create(
            company=self.company,
            client=self.client_b,
            name="Planning Project",
            status=ProjectStatus.PLANNING,
            priority="Low",
            assigned_to=self.user_b,
            start_date=datetime.date(2026, 6, 1),
            deadline=datetime.date(2026, 9, 1),
        )

    def test_filter_by_status(self):
        result = ProjectService.list_projects(company_id=self.company.id, status=ProjectStatus.DRAFT)
        self.assertEqual(list(result), [self.project_draft])

    def test_filter_by_client(self):
        result = ProjectService.list_projects(company_id=self.company.id, client_id=self.client_b.id)
        self.assertEqual(list(result), [self.project_planning])

    def test_filter_by_assigned_to(self):
        result = ProjectService.list_projects(company_id=self.company.id, assigned_to_id=self.user_a.id)
        self.assertEqual(list(result), [self.project_draft])

    def test_filter_by_priority(self):
        result = ProjectService.list_projects(company_id=self.company.id, priority="High")
        self.assertEqual(list(result), [self.project_draft])

    def test_filter_by_start_date_range(self):
        result = ProjectService.list_projects(
            company_id=self.company.id,
            start_date_from=datetime.date(2026, 5, 1),
            start_date_to=datetime.date(2026, 7, 1),
        )
        self.assertEqual(list(result), [self.project_planning])

    def test_filter_by_deadline_range(self):
        result = ProjectService.list_projects(
            company_id=self.company.id,
            deadline_from=datetime.date(2026, 1, 1),
            deadline_to=datetime.date(2026, 4, 1),
        )
        self.assertEqual(list(result), [self.project_draft])

    def test_combined_filters_narrow_results(self):
        result = ProjectService.list_projects(
            company_id=self.company.id, status=ProjectStatus.PLANNING, priority="Low"
        )
        self.assertEqual(list(result), [self.project_planning])

    def test_ordering_by_name_ascending(self):
        result = ProjectService.list_projects(company_id=self.company.id, ordering="name")
        self.assertEqual(list(result), [self.project_draft, self.project_planning])

    def test_ordering_by_deadline_descending(self):
        result = ProjectService.list_projects(company_id=self.company.id, ordering="-deadline")
        self.assertEqual(list(result), [self.project_planning, self.project_draft])

    def test_invalid_ordering_falls_back_to_default(self):
        """
        Falls back to -created_at (plus the id tie-breaker) rather than
        raising -- doesn't assert a specific order among rows whose
        created_at may tie (see selectors.list_projects's id tie-breaker
        comment), only that both rows are still returned.
        """
        result = ProjectService.list_projects(company_id=self.company.id, ordering="not_a_field")
        self.assertCountEqual(list(result), [self.project_draft, self.project_planning])

    def test_ordering_is_deterministic_when_created_at_ties(self):
        """
        Regression test (BE-030) forcing the exact collision that caused
        the original flake: two rows sharing an identical created_at
        (bypassing auto_now_add via .update(), since the normal create
        path can't reliably reproduce an OS-clock-resolution collision).
        Without the "id" tie-breaker selectors.list_projects added in
        BE-028, this ordering would be undefined and could vary per call.
        """
        tied_timestamp = self.project_draft.created_at
        Project.objects.filter(
            id__in=[self.project_draft.id, self.project_planning.id]
        ).update(created_at=tied_timestamp)

        first_call = list(ProjectService.list_projects(company_id=self.company.id))
        second_call = list(ProjectService.list_projects(company_id=self.company.id))

        self.assertEqual(first_call, second_call)
        self.assertEqual(
            {p.id for p in first_call}, {self.project_draft.id, self.project_planning.id}
        )


class ProjectListFilterEndpointTestCase(TestCase):
    """
    Integration tests for GET /projects filter/ordering query params (BE-028).
    """

    def setUp(self):
        self.client = APIClient()

        self.member_user = User.objects.create_user(
            email="alice@company1.com", name="Alice Member", password="StrongPassword123!"
        )
        self.member_token = str(CompanyUserAccessToken.for_user(self.member_user))

        self.company1 = Company.objects.create(name="Studio One", status=CompanyStatus.ACTIVE)
        make_full_access_membership(self.company1, self.member_user)

        self.client1 = Client.objects.create(company=self.company1, name="Client One")

        self.project_draft = Project.objects.create(
            company=self.company1, client=self.client1, name="Draft Project", status=ProjectStatus.DRAFT
        )
        self.project_planning = Project.objects.create(
            company=self.company1,
            client=self.client1,
            name="Planning Project",
            status=ProjectStatus.PLANNING,
        )

    def test_filter_by_status_query_param(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.member_token}")
        response = self.client.get("/projects", {"status": "planning"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()["data"]
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["name"], "Planning Project")

    def test_invalid_status_value_returns_400(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.member_token}")
        response = self.client.get("/projects", {"status": "not-a-real-status"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_invalid_ordering_value_returns_400(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.member_token}")
        response = self.client.get("/projects", {"ordering": "not_a_field"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_ordering_by_name_query_param(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.member_token}")
        response = self.client.get("/projects", {"ordering": "name"})

        data = response.json()["data"]
        self.assertEqual([p["name"] for p in data], ["Draft Project", "Planning Project"])

    def test_no_filters_returns_all(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.member_token}")
        response = self.client.get("/projects")
        self.assertEqual(len(response.json()["data"]), 2)
