import uuid

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from apps.authentication.tokens import CompanyUserAccessToken
from apps.clients.models import Client
from apps.company.models import Company, CompanyStatus
from apps.documents.models import Document
from apps.projects.models import Project
from apps.users.models import CompanyMembership, CompanyMembershipStatus

User = get_user_model()


class DocumentViewsTestCase(TestCase):
    """
    Integration test suite for the Document HTTP endpoints (BE-046).
    """

    def setUp(self):
        self.client = APIClient()

        self.member_user = User.objects.create_user(
            email="alice@company1.com", name="Alice Member", password="StrongPassword123!"
        )
        self.member_token = str(CompanyUserAccessToken.for_user(self.member_user))

        self.company1 = Company.objects.create(name="Studio One", status=CompanyStatus.ACTIVE)
        self.company2 = Company.objects.create(name="Studio Two", status=CompanyStatus.ACTIVE)

        CompanyMembership.objects.create(
            company=self.company1, user=self.member_user, status=CompanyMembershipStatus.ACTIVE
        )

        self.client1 = Client.objects.create(company=self.company1, name="Client One")
        self.client2 = Client.objects.create(company=self.company2, name="Client Two")

        self.project1 = Project.objects.create(
            company=self.company1, client=self.client1, name="Kitchen Remodel"
        )
        self.project_c2 = Project.objects.create(
            company=self.company2, client=self.client2, name="Office Fitout"
        )

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.member_token}")

    def test_unauthenticated_list_fails_401(self):
        self.client.credentials()
        response = self.client.get(f"/projects/{self.project1.id}/documents")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_list_cross_tenant_project_returns_404(self):
        response = self.client.get(f"/projects/{self.project_c2.id}/documents")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_create_document(self):
        response = self.client.post(
            f"/projects/{self.project1.id}/documents",
            {"fileUrl": "https://files.example.com/doc.pdf"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        data = response.json()["data"]
        self.assertEqual(data["entityType"], "project")
        self.assertEqual(data["version"], 1)
        self.assertEqual(data["uploadedById"], str(self.member_user.id))

    def test_create_document_missing_file_url_returns_400(self):
        response = self.client.post(f"/projects/{self.project1.id}/documents", {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_document_reupload_increments_version(self):
        entity_id = str(uuid.uuid4())
        self.client.post(
            f"/projects/{self.project1.id}/documents",
            {"fileUrl": "https://files.example.com/v1.pdf", "entityType": "quotation", "entityId": entity_id},
            format="json",
        )
        response = self.client.post(
            f"/projects/{self.project1.id}/documents",
            {"fileUrl": "https://files.example.com/v2.pdf", "entityType": "quotation", "entityId": entity_id},
            format="json",
        )
        self.assertEqual(response.json()["data"]["version"], 2)

    def test_list_filtered_by_entity(self):
        entity_id = str(uuid.uuid4())
        self.client.post(
            f"/projects/{self.project1.id}/documents",
            {"fileUrl": "https://files.example.com/a.pdf", "entityType": "quotation", "entityId": entity_id},
            format="json",
        )
        self.client.post(
            f"/projects/{self.project1.id}/documents",
            {"fileUrl": "https://files.example.com/b.pdf"},
            format="json",
        )

        response = self.client.get(
            f"/projects/{self.project1.id}/documents?entityType=quotation&entityId={entity_id}"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.json()["data"]), 1)

    def test_get_document_detail(self):
        document = Document.objects.create(
            company=self.company1, project=self.project1, entity_type="project", entity_id=self.project1.id,
            file_url="https://files.example.com/doc.pdf",
        )
        response = self.client.get(f"/documents/{document.id}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["data"]["id"], str(document.id))

    def test_get_document_detail_cross_tenant_returns_404(self):
        document = Document.objects.create(
            company=self.company2, project=self.project_c2, entity_type="project", entity_id=self.project_c2.id,
            file_url="https://files.example.com/doc.pdf",
        )
        response = self.client.get(f"/documents/{document.id}")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_delete_document(self):
        create_resp = self.client.post(
            f"/projects/{self.project1.id}/documents",
            {"fileUrl": "https://files.example.com/doc.pdf"},
            format="json",
        )
        document_id = create_resp.json()["data"]["id"]

        response = self.client.delete(f"/documents/{document_id}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        get_resp = self.client.get(f"/documents/{document_id}")
        self.assertEqual(get_resp.status_code, status.HTTP_404_NOT_FOUND)
