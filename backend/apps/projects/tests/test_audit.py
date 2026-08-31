import datetime
from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.audit.models import AuditLog
from apps.clients.models import Client
from apps.company.models import Company, CompanyStatus
from apps.projects.models import Project, ProjectStatus
from apps.projects.services import ProjectMemberService, ProjectService
from apps.users.models import CompanyMembership, CompanyMembershipStatus

User = get_user_model()


class ProjectAuditLogTestCase(TestCase):
    """
    Unit test suite for Project's audit log integration (BE-029).
    """

    def setUp(self):
        self.company = Company.objects.create(name="Alpha Corp", status=CompanyStatus.ACTIVE)
        self.client_obj = Client.objects.create(company=self.company, name="Client One")
        self.actor = User.objects.create_user(
            email="actor@company1.com", name="Actor", password="StrongPassword123!"
        )
        self.teammate = User.objects.create_user(
            email="teammate@company1.com", name="Teammate", password="StrongPassword123!"
        )
        CompanyMembership.objects.create(
            company=self.company, user=self.actor, status=CompanyMembershipStatus.ACTIVE
        )
        CompanyMembership.objects.create(
            company=self.company, user=self.teammate, status=CompanyMembershipStatus.ACTIVE
        )

    def test_create_project_writes_audit_log_entry(self):
        project = ProjectService.create_project(
            company_id=self.company.id,
            client_id=self.client_obj.id,
            name="Audited Project",
            actor_user=self.actor,
        )

        entry = AuditLog.objects.get(entity_type="project", entity_id=project.id, action="create")
        self.assertEqual(entry.company_id, self.company.id)
        self.assertEqual(entry.actor_user_id, self.actor.id)
        self.assertIsNone(entry.before_state)
        self.assertEqual(entry.after_state["name"], "Audited Project")
        self.assertEqual(entry.after_state["status"], ProjectStatus.DRAFT)
        self.assertEqual(entry.after_state["client_id"], str(self.client_obj.id))

    def test_create_project_with_dates_serializes_cleanly(self):
        """
        Regression guard: before this fix, a raw date object in
        after_state would raise TypeError at JSONField save time (this
        JSONField has no DjangoJSONEncoder configured).
        """
        project = ProjectService.create_project(
            company_id=self.company.id,
            client_id=self.client_obj.id,
            name="Dated Project",
            start_date=datetime.date(2026, 1, 15),
            deadline=datetime.date(2026, 6, 30),
        )

        entry = AuditLog.objects.get(entity_type="project", entity_id=project.id, action="create")
        self.assertEqual(entry.after_state["start_date"], "2026-01-15")
        self.assertEqual(entry.after_state["deadline"], "2026-06-30")

    def test_update_project_writes_before_and_after(self):
        project = ProjectService.create_project(
            company_id=self.company.id, client_id=self.client_obj.id, name="Original Name"
        )

        ProjectService.update_project(
            project_id=project.id,
            validated_data={"name": "Renamed Project"},
            actor_user=self.actor,
        )

        entry = AuditLog.objects.filter(
            entity_type="project", entity_id=project.id, action="update"
        ).latest("created_at")
        self.assertEqual(entry.before_state["name"], "Original Name")
        self.assertEqual(entry.after_state["name"], "Renamed Project")

    def test_soft_delete_project_writes_audit_log_entry(self):
        project = ProjectService.create_project(
            company_id=self.company.id, client_id=self.client_obj.id, name="Doomed Project"
        )
        project_id = project.id

        ProjectService.soft_delete_project(project_id, actor_user=self.actor)

        entry = AuditLog.objects.get(entity_type="project", entity_id=project_id, action="delete")
        self.assertEqual(entry.before_state["name"], "Doomed Project")
        self.assertIsNone(entry.after_state)

    def test_status_transition_writes_audit_log_as_update(self):
        project = ProjectService.create_project(
            company_id=self.company.id, client_id=self.client_obj.id, name="Transitioning Project"
        )

        ProjectService.transition_status(
            project_id=project.id, target_status=ProjectStatus.PLANNING, actor_user=self.actor
        )

        entry = AuditLog.objects.filter(
            entity_type="project", entity_id=project.id, action="update"
        ).latest("created_at")
        self.assertEqual(entry.before_state["status"], ProjectStatus.DRAFT)
        self.assertEqual(entry.after_state["status"], ProjectStatus.PLANNING)

    def test_failed_status_transition_writes_no_audit_entry(self):
        from apps.common.exceptions import ConflictError

        project = ProjectService.create_project(
            company_id=self.company.id, client_id=self.client_obj.id, name="Blocked Transition"
        )

        with self.assertRaises(ConflictError):
            ProjectService.transition_status(
                project_id=project.id, target_status=ProjectStatus.EXECUTION
            )

        # create_project() above already writes its own "create" entry --
        # assert no "update" entry (the transition-specific action) exists,
        # not that zero rows exist for this project at all.
        self.assertFalse(
            AuditLog.objects.filter(
                entity_type="project", entity_id=project.id, action="update"
            ).exists()
        )

    def test_add_member_writes_audit_log_entry(self):
        project = ProjectService.create_project(
            company_id=self.company.id, client_id=self.client_obj.id, name="Team Project"
        )

        member = ProjectMemberService.add_member(
            project=project, user_id=self.teammate.id, actor_user=self.actor
        )

        entry = AuditLog.objects.get(
            entity_type="project_member", entity_id=member.id, action="create"
        )
        self.assertEqual(entry.company_id, self.company.id)
        self.assertEqual(entry.actor_user_id, self.actor.id)
        self.assertEqual(entry.after_state["project_id"], str(project.id))
        self.assertEqual(entry.after_state["user_id"], str(self.teammate.id))

    def test_remove_member_writes_audit_log_entry(self):
        project = ProjectService.create_project(
            company_id=self.company.id, client_id=self.client_obj.id, name="Team Project"
        )
        member = ProjectMemberService.add_member(project=project, user_id=self.teammate.id)
        member_id = member.id

        ProjectMemberService.remove_member(
            project=project, user_id=self.teammate.id, actor_user=self.actor
        )

        entry = AuditLog.objects.get(
            entity_type="project_member", entity_id=member_id, action="delete"
        )
        self.assertEqual(entry.before_state["user_id"], str(self.teammate.id))
        self.assertIsNone(entry.after_state)
