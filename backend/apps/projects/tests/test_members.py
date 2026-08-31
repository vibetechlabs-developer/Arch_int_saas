import uuid
from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import exceptions as drf_exceptions
from rest_framework import status
from rest_framework.test import APIClient

from apps.authentication.tokens import CompanyUserAccessToken, PlatformAdminAccessToken
from apps.clients.models import Client
from apps.common.exceptions import ConflictError
from apps.company.models import Company, CompanyStatus
from apps.projects.models import Project, ProjectMember
from apps.projects.services import ProjectMemberService, ProjectService
from apps.users.models import CompanyMembership, CompanyMembershipStatus

User = get_user_model()


class ProjectMemberServiceTestCase(TestCase):
    """
    Unit test suite for ProjectMemberService business logic (BE-026).
    """

    def setUp(self):
        self.company1 = Company.objects.create(name="Alpha Corp", status=CompanyStatus.ACTIVE)
        self.company2 = Company.objects.create(name="Beta Corp", status=CompanyStatus.ACTIVE)

        self.client1 = Client.objects.create(company=self.company1, name="Client One")
        self.project1 = Project.objects.create(
            company=self.company1, client=self.client1, name="Kitchen Remodel"
        )

        self.member_user = User.objects.create_user(
            email="pm@company1.com", name="PM One", password="StrongPassword123!"
        )
        CompanyMembership.objects.create(
            company=self.company1, user=self.member_user, status=CompanyMembershipStatus.ACTIVE
        )

        self.other_company_user = User.objects.create_user(
            email="pm@company2.com", name="PM Two", password="StrongPassword123!"
        )
        CompanyMembership.objects.create(
            company=self.company2, user=self.other_company_user, status=CompanyMembershipStatus.ACTIVE
        )

        self.revoked_user = User.objects.create_user(
            email="revoked@company1.com", name="Revoked", password="StrongPassword123!"
        )
        CompanyMembership.objects.create(
            company=self.company1, user=self.revoked_user, status=CompanyMembershipStatus.REVOKED
        )

        self.adder = User.objects.create_user(
            email="admin@company1.com", name="Admin", password="StrongPassword123!"
        )
        CompanyMembership.objects.create(
            company=self.company1, user=self.adder, status=CompanyMembershipStatus.ACTIVE
        )

    def test_add_member_success(self):
        member = ProjectMemberService.add_member(
            project=self.project1, user_id=self.member_user.id, assigned_by_id=self.adder.id
        )
        self.assertEqual(member.project_id, self.project1.id)
        self.assertEqual(member.user_id, self.member_user.id)
        self.assertEqual(member.assigned_by_id, self.adder.id)
        self.assertEqual(member.company_id, self.company1.id)

    def test_add_member_without_assigned_by(self):
        member = ProjectMemberService.add_member(project=self.project1, user_id=self.member_user.id)
        self.assertIsNone(member.assigned_by)

    def test_add_member_wrong_company_rejected(self):
        with self.assertRaises(drf_exceptions.ValidationError):
            ProjectMemberService.add_member(project=self.project1, user_id=self.other_company_user.id)

    def test_add_member_revoked_membership_rejected(self):
        with self.assertRaises(drf_exceptions.ValidationError):
            ProjectMemberService.add_member(project=self.project1, user_id=self.revoked_user.id)

    def test_add_member_nonexistent_user_rejected(self):
        with self.assertRaises(drf_exceptions.ValidationError):
            ProjectMemberService.add_member(project=self.project1, user_id=uuid.uuid4())

    def test_add_duplicate_active_member_raises_conflict(self):
        ProjectMemberService.add_member(project=self.project1, user_id=self.member_user.id)
        with self.assertRaises(ConflictError):
            ProjectMemberService.add_member(project=self.project1, user_id=self.member_user.id)

    def test_readd_after_removal_succeeds(self):
        ProjectMemberService.add_member(project=self.project1, user_id=self.member_user.id)
        ProjectMemberService.remove_member(project=self.project1, user_id=self.member_user.id)

        member = ProjectMemberService.add_member(project=self.project1, user_id=self.member_user.id)
        self.assertIsNotNone(member.id)

    def test_list_members(self):
        ProjectMemberService.add_member(project=self.project1, user_id=self.member_user.id)
        ProjectMemberService.add_member(project=self.project1, user_id=self.adder.id)

        members = ProjectMemberService.list_members(self.project1)
        self.assertEqual(members.count(), 2)

    def test_remove_member_success(self):
        ProjectMemberService.add_member(project=self.project1, user_id=self.member_user.id)
        ProjectMemberService.remove_member(project=self.project1, user_id=self.member_user.id)

        self.assertEqual(ProjectMemberService.list_members(self.project1).count(), 0)
        self.assertTrue(
            ProjectMember.all_objects.filter(
                project=self.project1, user=self.member_user
            ).exists()
        )

    def test_remove_nonexistent_member_raises_not_found(self):
        with self.assertRaises(drf_exceptions.NotFound):
            ProjectMemberService.remove_member(project=self.project1, user_id=self.member_user.id)

    def test_assigned_to_and_team_membership_are_independent(self):
        """
        Adding a user to the team does not touch Project.assigned_to, and
        vice versa — the two mechanisms are additive, not overlapping
        (Backend Lead decision, BE-025/026 planning).
        """
        ProjectService.update_project(
            project_id=self.project1.id,
            validated_data={"assigned_to_id": self.member_user.id},
        )
        ProjectMemberService.add_member(project=self.project1, user_id=self.adder.id)

        self.project1.refresh_from_db()
        self.assertEqual(self.project1.assigned_to_id, self.member_user.id)
        self.assertEqual(ProjectMemberService.list_members(self.project1).count(), 1)
        self.assertEqual(
            ProjectMemberService.list_members(self.project1).first().user_id, self.adder.id
        )


class ProjectTeamViewTestCase(TestCase):
    """
    Integration test suite for the Project team endpoints (BE-026).
    """

    def setUp(self):
        self.client = APIClient()

        self.superadmin = User.objects.create_superuser(
            email="superadmin@example.com", name="Super Admin", password="StrongPassword123!"
        )
        self.superadmin_token = str(PlatformAdminAccessToken.for_user(self.superadmin))

        self.member_user = User.objects.create_user(
            email="alice@company1.com", name="Alice Member", password="StrongPassword123!"
        )
        self.member_token = str(CompanyUserAccessToken.for_user(self.member_user))

        self.teammate = User.objects.create_user(
            email="carol@company1.com", name="Carol Teammate", password="StrongPassword123!"
        )

        self.non_member_user = User.objects.create_user(
            email="bob@outsider.com", name="Bob Outsider", password="StrongPassword123!"
        )
        self.non_member_token = str(CompanyUserAccessToken.for_user(self.non_member_user))

        self.company1 = Company.objects.create(name="Studio One", status=CompanyStatus.ACTIVE)
        self.company2 = Company.objects.create(name="Studio Two", status=CompanyStatus.ACTIVE)

        CompanyMembership.objects.create(
            company=self.company1, user=self.member_user, status=CompanyMembershipStatus.ACTIVE
        )
        CompanyMembership.objects.create(
            company=self.company1, user=self.teammate, status=CompanyMembershipStatus.ACTIVE
        )

        self.client1 = Client.objects.create(company=self.company1, name="Client One")
        self.client2 = Client.objects.create(company=self.company2, name="Client Two")

        self.project1 = Project.objects.create(
            company=self.company1, client=self.client1, name="Kitchen Remodel"
        )
        self.project_c2 = Project.objects.create(
            company=self.company2, client=self.client2, name="Office Fitout"
        )

    def _url(self, project_id):
        return f"/projects/{project_id}/team"

    # --- Authentication / Authorization ---------------------------------

    def test_unauthenticated_requests_fail_401(self):
        response = self.client.get(self._url(self.project1.id))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_non_member_denied_403(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.non_member_token}")
        response = self.client.get(self._url(self.project1.id))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_cross_tenant_project_returns_404_not_403(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.member_token}")
        response = self.client.get(self._url(self.project_c2.id))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    # --- List / Add -------------------------------------------------------

    def test_list_team_empty(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.member_token}")
        response = self.client.get(self._url(self.project1.id))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["data"], [])

    def test_add_member_success(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.member_token}")
        response = self.client.post(self._url(self.project1.id), {"userId": str(self.teammate.id)})

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        data = response.json()["data"]
        self.assertEqual(data["userId"], str(self.teammate.id))
        self.assertEqual(data["userName"], "Carol Teammate")
        self.assertEqual(data["assignedById"], str(self.member_user.id))

    def test_add_member_then_list_reflects_it(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.member_token}")
        self.client.post(self._url(self.project1.id), {"userId": str(self.teammate.id)})

        response = self.client.get(self._url(self.project1.id))
        self.assertEqual(len(response.json()["data"]), 1)

    def test_add_member_wrong_company_rejected_400(self):
        outsider = User.objects.create_user(
            email="outsider2@example.com", name="Outsider Two", password="StrongPassword123!"
        )
        CompanyMembership.objects.create(
            company=self.company2, user=outsider, status=CompanyMembershipStatus.ACTIVE
        )

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.member_token}")
        response = self.client.post(self._url(self.project1.id), {"userId": str(outsider.id)})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_add_duplicate_member_returns_409(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.member_token}")
        self.client.post(self._url(self.project1.id), {"userId": str(self.teammate.id)})
        response = self.client.post(self._url(self.project1.id), {"userId": str(self.teammate.id)})
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)

    def test_add_member_missing_user_id_400(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.member_token}")
        response = self.client.post(self._url(self.project1.id), {})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_add_member_cross_tenant_project_404(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.member_token}")
        response = self.client.post(
            self._url(self.project_c2.id), {"userId": str(self.teammate.id)}
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_platform_admin_can_add_cross_tenant(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.superadmin_token}")
        response = self.client.post(
            self._url(self.project1.id), {"userId": str(self.teammate.id)}
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    # --- Remove -------------------------------------------------------------

    def test_remove_member_success(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.member_token}")
        self.client.post(self._url(self.project1.id), {"userId": str(self.teammate.id)})

        response = self.client.delete(f"{self._url(self.project1.id)}/{self.teammate.id}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        list_response = self.client.get(self._url(self.project1.id))
        self.assertEqual(list_response.json()["data"], [])

    def test_remove_nonexistent_member_404(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.member_token}")
        response = self.client.delete(f"{self._url(self.project1.id)}/{self.teammate.id}")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_remove_member_cross_tenant_project_404(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.member_token}")
        response = self.client.delete(f"{self._url(self.project_c2.id)}/{self.teammate.id}")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
