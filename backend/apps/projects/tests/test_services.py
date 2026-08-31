import uuid
from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import exceptions as drf_exceptions

from apps.clients.models import Client
from apps.company.models import Company, CompanyStatus
from apps.projects.models import Project, ProjectStatus
from apps.projects.services import ProjectService
from apps.users.models import CompanyMembership, CompanyMembershipStatus

User = get_user_model()


class ProjectServiceTestCase(TestCase):
    """
    Unit test suite for ProjectService business logic (BE-025).
    """

    def setUp(self):
        self.company1 = Company.objects.create(name="Alpha Corp", status=CompanyStatus.ACTIVE)
        self.company2 = Company.objects.create(name="Beta Corp", status=CompanyStatus.ACTIVE)

        self.client1 = Client.objects.create(company=self.company1, name="Client One")
        self.client2 = Client.objects.create(company=self.company2, name="Client Two")

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

        self.project1 = ProjectService.create_project(
            company_id=self.company1.id, client_id=self.client1.id, name="Kitchen Remodel"
        )
        self.project2 = ProjectService.create_project(
            company_id=self.company2.id, client_id=self.client2.id, name="Office Fitout"
        )

    def test_create_project_success(self):
        project = ProjectService.create_project(
            company_id=self.company1.id, client_id=self.client1.id, name="New Project"
        )
        self.assertEqual(project.name, "New Project")
        self.assertEqual(project.company_id, self.company1.id)
        self.assertEqual(project.client_id, self.client1.id)
        self.assertEqual(project.status, ProjectStatus.DRAFT)

    def test_create_project_nonexistent_company_raises_not_found(self):
        with self.assertRaises(drf_exceptions.NotFound):
            ProjectService.create_project(
                company_id=uuid.uuid4(), client_id=self.client1.id, name="Orphan Project"
            )

    def test_create_project_cross_tenant_client_raises_not_found(self):
        """
        Resolves BE-024's documented gap: Project.company_id ==
        Project.client.company_id, enforced by reusing
        ClientService.get_client_by_id's existing tenant check.
        """
        with self.assertRaises(drf_exceptions.NotFound):
            ProjectService.create_project(
                company_id=self.company1.id, client_id=self.client2.id, name="Cross Tenant Project"
            )

    def test_create_project_with_valid_assignee(self):
        project = ProjectService.create_project(
            company_id=self.company1.id,
            client_id=self.client1.id,
            name="Assigned Project",
            assigned_to_id=self.member_user.id,
        )
        self.assertEqual(project.assigned_to_id, self.member_user.id)

    def test_create_project_with_wrong_company_assignee_rejected(self):
        with self.assertRaises(drf_exceptions.ValidationError):
            ProjectService.create_project(
                company_id=self.company1.id,
                client_id=self.client1.id,
                name="Bad Assignee Project",
                assigned_to_id=self.other_company_user.id,
            )

    def test_create_project_with_revoked_membership_assignee_rejected(self):
        with self.assertRaises(drf_exceptions.ValidationError):
            ProjectService.create_project(
                company_id=self.company1.id,
                client_id=self.client1.id,
                name="Revoked Assignee Project",
                assigned_to_id=self.revoked_user.id,
            )

    def test_get_project_by_id_success(self):
        project = ProjectService.get_project_by_id(self.project1.id)
        self.assertEqual(project.id, self.project1.id)

    def test_get_project_by_id_cross_tenant_raises_not_found(self):
        with self.assertRaises(drf_exceptions.NotFound):
            ProjectService.get_project_by_id(self.project1.id, company_id=self.company2.id)

    def test_list_projects_filtering_by_company(self):
        projects_c1 = ProjectService.list_projects(company_id=self.company1.id)
        self.assertEqual(projects_c1.count(), 1)
        self.assertEqual(projects_c1.first().id, self.project1.id)

    def test_list_projects_for_viewer_platform_admin_sees_all(self):
        queryset = ProjectService.list_projects_for_viewer(
            is_platform_admin=True, resolved_company_id=None, admin_company_id_param=None
        )
        self.assertEqual(queryset.count(), 2)

    def test_resolve_create_target_company_id_non_admin_mismatch_denied(self):
        with self.assertRaises(drf_exceptions.PermissionDenied):
            ProjectService.resolve_create_target_company_id(
                is_platform_admin=False,
                resolved_company_id=self.company1.id,
                supplied_company_id=self.company2.id,
            )

    def test_update_project_success(self):
        updated = ProjectService.update_project(
            project_id=self.project1.id,
            validated_data={"name": "Renamed Project", "priority": "High"},
        )
        self.assertEqual(updated.name, "Renamed Project")
        self.assertEqual(updated.priority, "High")

    def test_update_project_cross_tenant_raises_not_found(self):
        with self.assertRaises(drf_exceptions.NotFound):
            ProjectService.update_project(
                project_id=self.project1.id,
                validated_data={"name": "Hacked"},
                company_id=self.company2.id,
            )

    def test_update_project_assigned_to_wrong_company_rejected(self):
        with self.assertRaises(drf_exceptions.ValidationError):
            ProjectService.update_project(
                project_id=self.project1.id,
                validated_data={"assigned_to_id": self.other_company_user.id},
            )

    def test_update_project_assigned_to_can_be_cleared(self):
        ProjectService.update_project(
            project_id=self.project1.id,
            validated_data={"assigned_to_id": self.member_user.id},
        )
        updated = ProjectService.update_project(
            project_id=self.project1.id,
            validated_data={"assigned_to_id": None},
        )
        self.assertIsNone(updated.assigned_to)

    def test_update_project_does_not_expose_status_or_client_changes(self):
        """
        update_project's validated_data contract never includes
        "status"/"client_id" keys from the serializer layer — this test
        documents that even if such keys were somehow passed, the service
        does not act on them (defense in depth, not the primary boundary).
        """
        updated = ProjectService.update_project(
            project_id=self.project1.id,
            validated_data={"status": "completed", "client_id": str(self.client2.id)},
        )
        self.assertEqual(updated.status, ProjectStatus.DRAFT)
        self.assertEqual(updated.client_id, self.client1.id)

    def test_soft_delete_project(self):
        project_id = self.project1.id
        ProjectService.soft_delete_project(project_id)

        with self.assertRaises(drf_exceptions.NotFound):
            ProjectService.get_project_by_id(project_id)

        self.assertTrue(Project.all_objects.filter(id=project_id).exists())
