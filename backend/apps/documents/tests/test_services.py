import uuid

from django.test import TestCase
from rest_framework import exceptions as drf_exceptions

from apps.clients.models import Client
from apps.company.models import Company, CompanyStatus
from apps.documents.services import DocumentService
from apps.projects.models import Project


class DocumentServiceCreateTestCase(TestCase):
    """
    Unit test suite for DocumentService.create_document (BE-046).
    """

    def setUp(self):
        self.company = Company.objects.create(name="Studio One", status=CompanyStatus.ACTIVE)
        self.client_obj = Client.objects.create(company=self.company, name="Jane Doe")
        self.project = Project.objects.create(
            company=self.company, client=self.client_obj, name="Kitchen Remodel"
        )

    def test_create_document_defaults_to_project_entity(self):
        document = DocumentService.create_document(
            project=self.project, file_url="https://files.example.com/doc.pdf"
        )
        self.assertEqual(document.entity_type, "project")
        self.assertEqual(document.entity_id, self.project.id)
        self.assertEqual(document.version, 1)

    def test_create_document_with_explicit_entity(self):
        quotation_id = uuid.uuid4()
        document = DocumentService.create_document(
            project=self.project,
            file_url="https://files.example.com/quote.pdf",
            entity_type="quotation",
            entity_id=quotation_id,
        )
        self.assertEqual(document.entity_type, "quotation")
        self.assertEqual(document.entity_id, quotation_id)

    def test_create_document_second_upload_increments_version(self):
        quotation_id = uuid.uuid4()
        DocumentService.create_document(
            project=self.project, file_url="https://files.example.com/v1.pdf",
            entity_type="quotation", entity_id=quotation_id,
        )
        second = DocumentService.create_document(
            project=self.project, file_url="https://files.example.com/v2.pdf",
            entity_type="quotation", entity_id=quotation_id,
        )
        self.assertEqual(second.version, 2)

    def test_create_document_different_entities_version_independently(self):
        first = DocumentService.create_document(
            project=self.project, file_url="https://files.example.com/a.pdf",
            entity_type="quotation", entity_id=uuid.uuid4(),
        )
        second = DocumentService.create_document(
            project=self.project, file_url="https://files.example.com/b.pdf",
            entity_type="quotation", entity_id=uuid.uuid4(),
        )
        self.assertEqual(first.version, 1)
        self.assertEqual(second.version, 1)

    def test_create_document_blank_file_url_and_no_storage_key_raises_validation_error(self):
        """
        BE-078: create_document now requires exactly one file source
        (fileUrl or fileStorageKey) -- neither supplied (or fileUrl is
        blank/whitespace-only) raises a proper DRF ValidationError (400),
        not a bare ValueError.
        """
        with self.assertRaises(drf_exceptions.ValidationError):
            DocumentService.create_document(project=self.project, file_url="   ")

    def test_create_document_both_file_url_and_storage_key_raises_validation_error(self):
        with self.assertRaises(drf_exceptions.ValidationError):
            DocumentService.create_document(
                project=self.project,
                file_url="https://files.example.com/doc.pdf",
                file_storage_key="documents/some-company/some-key.pdf",
            )

    def test_create_document_with_storage_key_only_succeeds(self):
        document = DocumentService.create_document(
            project=self.project, file_storage_key="documents/some-company/some-key.pdf"
        )
        self.assertEqual(document.file_storage_key, "documents/some-company/some-key.pdf")
        self.assertEqual(document.file_url, "")


class DocumentServiceGetAndDeleteTestCase(TestCase):
    """
    Unit test suite for DocumentService.get_document_by_id/
    soft_delete_document (BE-046).
    """

    def setUp(self):
        self.company = Company.objects.create(name="Studio One", status=CompanyStatus.ACTIVE)
        self.client_obj = Client.objects.create(company=self.company, name="Jane Doe")
        self.project = Project.objects.create(
            company=self.company, client=self.client_obj, name="Kitchen Remodel"
        )
        self.document = DocumentService.create_document(
            project=self.project, file_url="https://files.example.com/doc.pdf"
        )

    def test_get_by_id_success(self):
        found = DocumentService.get_document_by_id(self.document.id)
        self.assertEqual(found.id, self.document.id)

    def test_get_by_id_cross_tenant_raises_not_found(self):
        other_company = Company.objects.create(name="Studio Two", status=CompanyStatus.ACTIVE)
        with self.assertRaises(drf_exceptions.NotFound):
            DocumentService.get_document_by_id(self.document.id, company_id=other_company.id)

    def test_soft_delete_document(self):
        document_id = self.document.id
        DocumentService.soft_delete_document(self.document)
        with self.assertRaises(drf_exceptions.NotFound):
            DocumentService.get_document_by_id(document_id)
