import uuid

from django.test import TestCase

from apps.clients.models import Client
from apps.company.models import Company, CompanyStatus
from apps.documents.models import Document
from apps.projects.models import Project


class DocumentModelTestCase(TestCase):
    """
    Unit test suite for Document domain model (BE-046).
    """

    def setUp(self):
        self.company = Company.objects.create(name="Test Company", status=CompanyStatus.ACTIVE)
        self.client_obj = Client.objects.create(company=self.company, name="Jane Doe")
        self.project = Project.objects.create(
            company=self.company, client=self.client_obj, name="Kitchen Remodel"
        )

    def _create_document(self, **overrides):
        fields = dict(
            company=self.company,
            project=self.project,
            entity_type="project",
            entity_id=self.project.id,
            file_url="https://files.example.com/doc.pdf",
        )
        fields.update(overrides)
        return Document.objects.create(**fields)

    def test_document_creation_defaults(self):
        document = self._create_document()
        self.assertIsInstance(document.id, uuid.UUID)
        self.assertEqual(document.version, 1)
        self.assertIsNone(document.uploaded_by)
        self.assertFalse(document.is_deleted)

    def test_document_has_no_uploaded_at_column(self):
        self.assertFalse(hasattr(Document, "uploaded_at"))

    def test_document_str_representation(self):
        document = self._create_document()
        self.assertEqual(str(document), f"project:{self.project.id} v1")

    def test_document_requires_project(self):
        with self.assertRaises(Exception):
            Document.objects.create(
                company=self.company, entity_type="project", entity_id=self.project.id,
                file_url="https://files.example.com/doc.pdf",
            )

    def test_document_cascade_delete_with_project(self):
        document = self._create_document()
        document_id = document.id
        self.project.delete(hard=True)
        self.assertFalse(Document.all_objects.filter(id=document_id).exists())

    def test_document_soft_delete_lifecycle(self):
        document = self._create_document()
        document_id = document.id

        document.delete()
        self.assertTrue(document.is_deleted)
        self.assertFalse(Document.objects.filter(id=document_id).exists())
        self.assertTrue(Document.all_objects.filter(id=document_id).exists())

        document.restore()
        self.assertTrue(Document.objects.filter(id=document_id).exists())

    def test_reverse_accessor_from_project(self):
        self._create_document()
        self.assertEqual(self.project.documents.count(), 1)
