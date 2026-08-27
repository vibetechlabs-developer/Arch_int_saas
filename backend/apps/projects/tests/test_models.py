import uuid
from django.core.exceptions import ValidationError
from django.db.models import ProtectedError
from django.test import TestCase

from apps.clients.models import Client
from apps.company.models import Company, CompanyStatus
from apps.projects.models import Project, ProjectStatus
from apps.users.models import User


class ProjectModelTestCase(TestCase):
    """
    Unit test suite for Project domain model (BE-024).
    """

    def setUp(self):
        self.company = Company.objects.create(name="Test Company", status=CompanyStatus.ACTIVE)
        self.other_company = Company.objects.create(name="Other Company", status=CompanyStatus.ACTIVE)
        self.client_obj = Client.objects.create(company=self.company, name="Jane Doe")
        self.user = User.objects.create_user(
            email="pm@example.com", name="Project Manager", password="StrongPassword123!"
        )

    def test_project_creation_with_required_fields_only(self):
        project = Project.objects.create(
            company=self.company, client=self.client_obj, name="Kitchen Remodel"
        )
        self.assertIsInstance(project.id, uuid.UUID)
        self.assertEqual(project.name, "Kitchen Remodel")
        self.assertEqual(project.company, self.company)
        self.assertEqual(project.client, self.client_obj)
        self.assertIsNotNone(project.created_at)
        self.assertIsNotNone(project.updated_at)
        self.assertIsNone(project.deleted_at)
        self.assertFalse(project.is_deleted)

    def test_project_requires_company(self):
        with self.assertRaises(Exception):
            Project.objects.create(client=self.client_obj, name="No Company Project")

    def test_project_requires_client(self):
        with self.assertRaises(Exception):
            Project.objects.create(company=self.company, name="No Client Project")

    def test_project_requires_name(self):
        project = Project(company=self.company, client=self.client_obj, name="")
        with self.assertRaises(ValidationError):
            project.full_clean()

    def test_project_optional_field_defaults(self):
        project = Project.objects.create(
            company=self.company, client=self.client_obj, name="Kitchen Remodel"
        )
        self.assertIsNone(project.start_date)
        self.assertIsNone(project.deadline)
        self.assertEqual(project.priority, "")
        self.assertIsNone(project.assigned_to)
        self.assertIsNone(project.follow_up_reminder_at)

    def test_project_status_defaults_to_draft(self):
        project = Project.objects.create(
            company=self.company, client=self.client_obj, name="Kitchen Remodel"
        )
        self.assertEqual(project.status, ProjectStatus.DRAFT)
        self.assertEqual(project.status, "draft")

    def test_project_accepts_every_documented_status_value(self):
        for value, _label in ProjectStatus.choices:
            project = Project(
                company=self.company,
                client=self.client_obj,
                name=f"Project {value}",
                status=value,
            )
            project.full_clean()  # raises if the choice is somehow rejected
            project.save()
            project.refresh_from_db()
            self.assertEqual(project.status, value)

    def test_project_priority_accepts_arbitrary_text(self):
        """
        No documented value domain exists for priority (Backend Lead
        decision, 2026-08-27) — any free text must be accepted.
        """
        project = Project.objects.create(
            company=self.company,
            client=self.client_obj,
            name="Urgent Job",
            priority="URGENT-P0-CUSTOM-LABEL",
        )
        project.refresh_from_db()
        self.assertEqual(project.priority, "URGENT-P0-CUSTOM-LABEL")

    def test_project_str_representation(self):
        project = Project.objects.create(
            company=self.company, client=self.client_obj, name="Kitchen Remodel"
        )
        self.assertEqual(str(project), f"Kitchen Remodel ({self.company.name})")

    # --- Soft delete -------------------------------------------------------

    def test_project_soft_delete_lifecycle(self):
        project = Project.objects.create(
            company=self.company, client=self.client_obj, name="Kitchen Remodel"
        )
        project_id = project.id

        project.delete()
        self.assertTrue(project.is_deleted)
        self.assertIsNotNone(project.deleted_at)

        self.assertFalse(Project.objects.filter(id=project_id).exists())
        self.assertTrue(Project.all_objects.filter(id=project_id).exists())
        self.assertTrue(Project.deleted_objects.filter(id=project_id).exists())

        project.restore()
        self.assertFalse(project.is_deleted)
        self.assertIsNone(project.deleted_at)
        self.assertTrue(Project.objects.filter(id=project_id).exists())

    # --- FK deletion behavior -----------------------------------------------

    def test_company_field_on_delete_is_cascade(self):
        """
        Confirms Project.company is configured as CASCADE (structural
        field check). This cannot be exercised end-to-end via an actual
        Company.delete(hard=True) call in isolation — see the test below:
        because every Project requires a Client, and Client.company is
        ALSO CASCADE, deleting a Company with any Project always
        triggers Client->Project's PROTECT relation first, regardless of
        Project.company's own CASCADE setting. Verified empirically, not
        assumed.
        """
        field = Project._meta.get_field("company")
        self.assertEqual(field.remote_field.on_delete.__name__, "CASCADE")

    def test_company_hard_delete_blocked_by_protect_via_client_when_project_exists(self):
        """
        Real, verified Django behavior (not assumed): hard-deleting a
        Company CASCADEs to its Clients (Client.company=CASCADE) AND to
        its Projects (Project.company=CASCADE) in the same operation, but
        Django's deletion collector evaluates the Client->Project PROTECT
        relation independently — it does NOT treat a Project as "already
        being deleted anyway via the Company->Project path" when checking
        whether deleting its Client is protected. The net effect: hard-
        deleting a Company with any Client that has any Project raises
        ProtectedError, even though every affected row belongs to that
        same Company. This is a genuine consequence of Project.client's
        PROTECT choice (Naming_Standards.md §4), not a bug — documented in
        BACKEND_TASKS.md as a known constraint for any future tenant-
        offboarding feature (which must delete Projects, then Clients,
        then Company explicitly, rather than a single cascading call).
        """
        Project.objects.create(company=self.company, client=self.client_obj, name="Kitchen Remodel")

        with self.assertRaises(ProtectedError):
            self.company.delete(hard=True)

    def test_client_soft_delete_does_not_affect_project(self):
        """
        SoftDeleteModel.delete() never calls super().delete() — a
        soft-deleted client's row still physically exists, so the
        project's client_id FK stays valid with no extra code required.
        """
        project = Project.objects.create(
            company=self.company, client=self.client_obj, name="Kitchen Remodel"
        )
        self.client_obj.delete()  # soft delete only

        project.refresh_from_db()
        self.assertEqual(project.client_id, self.client_obj.id)

    def test_client_hard_delete_blocked_by_protect_when_project_exists(self):
        """
        Project.client uses on_delete=PROTECT (Naming_Standards.md §4) —
        a hard delete of a Client with an existing Project must be
        blocked at the database level, distinct from the soft-delete
        guard in ClientService (which is a separate, service-layer check).
        """
        Project.objects.create(company=self.company, client=self.client_obj, name="Kitchen Remodel")

        with self.assertRaises(ProtectedError):
            self.client_obj.delete(hard=True)

    def test_client_hard_delete_allowed_when_no_project_references_it(self):
        lonely_client = Client.objects.create(company=self.company, name="No Projects Client")
        # Should not raise.
        lonely_client.delete(hard=True)
        self.assertFalse(Client.all_objects.filter(id=lonely_client.id).exists())

    def test_assigned_to_set_null_on_user_hard_delete(self):
        project = Project.objects.create(
            company=self.company,
            client=self.client_obj,
            name="Kitchen Remodel",
            assigned_to=self.user,
        )
        self.user.delete(hard=True)

        project.refresh_from_db()
        self.assertIsNone(project.assigned_to)

    # --- Indexes -------------------------------------------------------------

    def test_company_status_composite_index_exists(self):
        index_names = {index.name for index in Project._meta.indexes}
        self.assertIn("project_company_status_idx", index_names)

        matching_index = next(
            i for i in Project._meta.indexes if i.name == "project_company_status_idx"
        )
        self.assertEqual(matching_index.fields, ["company", "status"])
