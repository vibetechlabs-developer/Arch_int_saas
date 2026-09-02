import uuid

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from apps.audit.models import AuditAction
from apps.audit.services import AuditLogService
from apps.authentication.tokens import CompanyUserAccessToken
from apps.company.models import Company, CompanyStatus
from apps.users.models import CompanyMembership, CompanyMembershipStatus

User = get_user_model()


class ActivityLogListViewTestCase(TestCase):
    """
    Integration test suite for `GET /activity-logs` (BE-047).
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

        AuditLogService.record(
            action=AuditAction.CREATE, entity_type="role", entity_id=uuid.uuid4(),
            company_id=self.company1.id, actor_user=self.member_user,
        )
        AuditLogService.record(
            action=AuditAction.CREATE, entity_type="role", entity_id=uuid.uuid4(), company_id=self.company2.id,
        )

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.member_token}")

    def test_unauthenticated_fails_401(self):
        self.client.credentials()
        response = self.client.get("/activity-logs")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_list_scoped_to_own_company(self):
        response = self.client.get("/activity-logs")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()["data"]
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["companyId"], str(self.company1.id))
        self.assertEqual(data[0]["actorUserName"], "Alice Member")

    def test_filter_by_entity_type(self):
        AuditLogService.record(
            action=AuditAction.CREATE, entity_type="client", entity_id=uuid.uuid4(), company_id=self.company1.id,
        )
        response = self.client.get("/activity-logs?entityType=client")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()["data"]
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["entityType"], "client")
