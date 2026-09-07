from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from apps.authentication.tokens import CompanyUserAccessToken
from apps.clients.models import Client
from apps.common.exceptions import ConflictError
from apps.common.test_utils import make_full_access_membership
from apps.company.models import Company, CompanyStatus
from apps.projects.models import Project, ProjectStatus, get_allowed_next_statuses
from apps.projects.services import ProjectService
from apps.users.models import CompanyMembership, CompanyMembershipStatus

User = get_user_model()


class GetAllowedNextStatusesTestCase(TestCase):
    """
    Unit tests for the pure BE-027 transition graph function.
    """

    def test_terminal_statuses_have_no_transitions(self):
        self.assertEqual(get_allowed_next_statuses(ProjectStatus.COMPLETED), set())
        self.assertEqual(get_allowed_next_statuses(ProjectStatus.CANCELLED), set())

    def test_draft_can_move_to_planning_or_on_hold_or_cancelled(self):
        allowed = get_allowed_next_statuses(ProjectStatus.DRAFT)
        self.assertEqual(allowed, {ProjectStatus.PLANNING, ProjectStatus.ON_HOLD, ProjectStatus.CANCELLED})

    def test_no_skipping_ahead(self):
        allowed = get_allowed_next_statuses(ProjectStatus.DRAFT)
        self.assertNotIn(ProjectStatus.EXECUTION, allowed)

    def test_no_moving_backward(self):
        allowed = get_allowed_next_statuses(ProjectStatus.EXECUTION)
        self.assertNotIn(ProjectStatus.DESIGN, allowed)
        self.assertNotIn(ProjectStatus.DRAFT, allowed)

    def test_handover_can_reach_completed(self):
        allowed = get_allowed_next_statuses(ProjectStatus.HANDOVER)
        self.assertIn(ProjectStatus.COMPLETED, allowed)

    def test_every_main_chain_status_can_reach_cancelled(self):
        for chain_status in (
            ProjectStatus.DRAFT,
            ProjectStatus.PLANNING,
            ProjectStatus.DESIGN,
            ProjectStatus.QUOTATION,
            ProjectStatus.APPROVED,
            ProjectStatus.EXECUTION,
            ProjectStatus.QUALITY_CHECK,
            ProjectStatus.HANDOVER,
        ):
            self.assertIn(ProjectStatus.CANCELLED, get_allowed_next_statuses(chain_status))

    def test_on_hold_without_recorded_prior_status_only_allows_cancelled(self):
        self.assertEqual(get_allowed_next_statuses(ProjectStatus.ON_HOLD), {ProjectStatus.CANCELLED})

    def test_on_hold_with_recorded_prior_status_allows_resume_and_cancel(self):
        allowed = get_allowed_next_statuses(ProjectStatus.ON_HOLD, status_before_hold=ProjectStatus.EXECUTION)
        self.assertEqual(allowed, {ProjectStatus.EXECUTION, ProjectStatus.CANCELLED})

    def test_on_hold_cannot_resume_to_a_different_status_than_recorded(self):
        allowed = get_allowed_next_statuses(ProjectStatus.ON_HOLD, status_before_hold=ProjectStatus.EXECUTION)
        self.assertNotIn(ProjectStatus.DESIGN, allowed)


class ProjectTransitionServiceTestCase(TestCase):
    """
    Unit tests for ProjectService.transition_status (BE-027).
    """

    def setUp(self):
        self.company = Company.objects.create(name="Alpha Corp", status=CompanyStatus.ACTIVE)
        self.other_company = Company.objects.create(name="Beta Corp", status=CompanyStatus.ACTIVE)
        self.client_obj = Client.objects.create(company=self.company, name="Client One")
        self.project = Project.objects.create(
            company=self.company, client=self.client_obj, name="Kitchen Remodel"
        )

    def test_valid_forward_transition(self):
        updated = ProjectService.transition_status(self.project.id, ProjectStatus.PLANNING)
        self.assertEqual(updated.status, ProjectStatus.PLANNING)

    def test_invalid_skip_ahead_raises_conflict(self):
        with self.assertRaises(ConflictError):
            ProjectService.transition_status(self.project.id, ProjectStatus.EXECUTION)

    def test_invalid_backward_move_raises_conflict(self):
        ProjectService.transition_status(self.project.id, ProjectStatus.PLANNING)
        ProjectService.transition_status(self.project.id, ProjectStatus.DESIGN)

        with self.assertRaises(ConflictError):
            ProjectService.transition_status(self.project.id, ProjectStatus.PLANNING)

    def test_terminal_status_rejects_any_transition(self):
        ProjectService.transition_status(self.project.id, ProjectStatus.CANCELLED)

        with self.assertRaises(ConflictError):
            ProjectService.transition_status(self.project.id, ProjectStatus.PLANNING)

    def test_hold_then_resume_returns_to_exact_prior_status(self):
        ProjectService.transition_status(self.project.id, ProjectStatus.PLANNING)
        ProjectService.transition_status(self.project.id, ProjectStatus.DESIGN)

        held = ProjectService.transition_status(self.project.id, ProjectStatus.ON_HOLD)
        self.assertEqual(held.status, ProjectStatus.ON_HOLD)
        self.assertEqual(held.status_before_hold, ProjectStatus.DESIGN)

        resumed = ProjectService.transition_status(self.project.id, ProjectStatus.DESIGN)
        self.assertEqual(resumed.status, ProjectStatus.DESIGN)
        self.assertEqual(resumed.status_before_hold, "")

    def test_hold_cannot_resume_to_a_different_status(self):
        ProjectService.transition_status(self.project.id, ProjectStatus.PLANNING)
        ProjectService.transition_status(self.project.id, ProjectStatus.ON_HOLD)

        with self.assertRaises(ConflictError):
            ProjectService.transition_status(self.project.id, ProjectStatus.EXECUTION)

    def test_hold_can_be_cancelled(self):
        ProjectService.transition_status(self.project.id, ProjectStatus.PLANNING)
        ProjectService.transition_status(self.project.id, ProjectStatus.ON_HOLD)

        cancelled = ProjectService.transition_status(self.project.id, ProjectStatus.CANCELLED)
        self.assertEqual(cancelled.status, ProjectStatus.CANCELLED)

    def test_draft_can_be_held_and_resumed(self):
        held = ProjectService.transition_status(self.project.id, ProjectStatus.ON_HOLD)
        self.assertEqual(held.status_before_hold, ProjectStatus.DRAFT)

        resumed = ProjectService.transition_status(self.project.id, ProjectStatus.DRAFT)
        self.assertEqual(resumed.status, ProjectStatus.DRAFT)

    def test_cross_tenant_transition_raises_not_found(self):
        from rest_framework import exceptions as drf_exceptions

        with self.assertRaises(drf_exceptions.NotFound):
            ProjectService.transition_status(
                self.project.id, ProjectStatus.PLANNING, company_id=self.other_company.id
            )


class ProjectStatusEndpointTestCase(TestCase):
    """
    Integration tests for PATCH /projects/{id}/status (BE-027).
    """

    def setUp(self):
        self.client = APIClient()

        self.member_user = User.objects.create_user(
            email="alice@company1.com", name="Alice Member", password="StrongPassword123!"
        )
        self.member_token = str(CompanyUserAccessToken.for_user(self.member_user))

        self.company1 = Company.objects.create(name="Studio One", status=CompanyStatus.ACTIVE)
        self.company2 = Company.objects.create(name="Studio Two", status=CompanyStatus.ACTIVE)

        make_full_access_membership(self.company1, self.member_user)

        self.client1 = Client.objects.create(company=self.company1, name="Client One")
        self.client2 = Client.objects.create(company=self.company2, name="Client Two")

        self.project1 = Project.objects.create(
            company=self.company1, client=self.client1, name="Kitchen Remodel"
        )
        self.project_c2 = Project.objects.create(
            company=self.company2, client=self.client2, name="Office Fitout"
        )

    def _url(self, project_id):
        return f"/projects/{project_id}/status"

    def test_unauthenticated_401(self):
        response = self.client.patch(self._url(self.project1.id), {"status": "planning"})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_valid_transition_success(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.member_token}")
        response = self.client.patch(
            self._url(self.project1.id), {"status": "planning"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["data"]["status"], "planning")

    def test_invalid_transition_returns_409(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.member_token}")
        response = self.client.patch(
            self._url(self.project1.id), {"status": "execution"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)

    def test_garbage_status_value_returns_400(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.member_token}")
        response = self.client.patch(
            self._url(self.project1.id), {"status": "not-a-real-status"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_missing_status_returns_400(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.member_token}")
        response = self.client.patch(self._url(self.project1.id), {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_cross_tenant_project_returns_404(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.member_token}")
        response = self.client.patch(
            self._url(self.project_c2.id), {"status": "planning"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_hold_and_resume_round_trip(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.member_token}")
        self.client.patch(self._url(self.project1.id), {"status": "planning"}, format="json")

        hold_response = self.client.patch(
            self._url(self.project1.id), {"status": "on_hold"}, format="json"
        )
        self.assertEqual(hold_response.status_code, status.HTTP_200_OK)
        self.assertEqual(hold_response.json()["data"]["status"], "on_hold")

        resume_response = self.client.patch(
            self._url(self.project1.id), {"status": "planning"}, format="json"
        )
        self.assertEqual(resume_response.status_code, status.HTTP_200_OK)
        self.assertEqual(resume_response.json()["data"]["status"], "planning")
