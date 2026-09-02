import uuid
from django.test import TestCase

from apps.audit.models import AuditAction, AuditLog
from apps.audit.services import ActivityLogService, AuditLogService
from apps.company.models import Company
from apps.users.models import User


class _FakeRequest:
    """Minimal stand-in for a DRF/Django request, for testing context extraction."""

    def __init__(self, request_id=None, meta=None):
        self.request_id = request_id
        self.META = meta or {}


class AuditLogServiceTestCase(TestCase):
    """
    Unit tests for AuditLogService (BE-019).
    """

    def setUp(self):
        self.company = Company.objects.create(name="Service Test Co")
        self.user = User.objects.create_user(
            email="actor@example.com", name="Actor", password="StrongPassword123!"
        )

    def test_record_persists_row_and_returns_it(self):
        entity_id = uuid.uuid4()

        entry = AuditLogService.record(
            action=AuditAction.CREATE,
            entity_type="role",
            entity_id=entity_id,
            company_id=self.company.id,
            actor_user=self.user,
            after_state={"name": "Accountant", "description": "", "is_active": True},
        )

        self.assertTrue(AuditLog.objects.filter(id=entry.id).exists())
        self.assertEqual(entry.entity_type, "role")
        self.assertEqual(entry.entity_id, entity_id)
        self.assertEqual(entry.company_id, self.company.id)
        self.assertEqual(entry.actor_user_id, self.user.id)
        self.assertEqual(entry.action, "create")

    def test_unregistered_entity_type_yields_empty_state_not_raw_dump(self):
        """
        Redaction safety net: an entity_type with no registered allowlist
        must never persist an unreviewed field set.
        """
        entry = AuditLogService.record(
            action=AuditAction.CREATE,
            entity_type="totally_unregistered_entity",
            entity_id=uuid.uuid4(),
            after_state={"password": "should-never-be-stored", "secret_token": "xyz"},
        )

        self.assertEqual(entry.after_state, {})

    def test_only_allowlisted_fields_are_persisted(self):
        """
        Even a well-intentioned caller accidentally including an
        unregistered field (e.g. copy-pasting a broader dict) must have it
        silently stripped, never persisted into the never-expired table.
        """
        entry = AuditLogService.record(
            action=AuditAction.UPDATE,
            entity_type="role",
            entity_id=uuid.uuid4(),
            before_state={"name": "Old Name", "internal_debug_flag": True},
            after_state={"name": "New Name", "internal_debug_flag": False},
        )

        self.assertEqual(entry.before_state, {"name": "Old Name"})
        self.assertEqual(entry.after_state, {"name": "New Name"})
        self.assertNotIn("internal_debug_flag", entry.before_state)
        self.assertNotIn("internal_debug_flag", entry.after_state)

    def test_none_before_and_after_state_stay_none(self):
        entry = AuditLogService.record(
            action=AuditAction.DELETE,
            entity_type="role",
            entity_id=uuid.uuid4(),
            before_state=None,
            after_state=None,
        )

        self.assertIsNone(entry.before_state)
        self.assertIsNone(entry.after_state)

    def test_request_context_extracted_when_present(self):
        fake_request = _FakeRequest(
            request_id="req_deadbeef0001",
            meta={
                "HTTP_USER_AGENT": "TestClient/1.0",
                "REMOTE_ADDR": "192.0.2.10",
            },
        )

        entry = AuditLogService.record(
            action=AuditAction.CREATE,
            entity_type="role",
            entity_id=uuid.uuid4(),
            request=fake_request,
        )

        self.assertEqual(entry.request_id, "req_deadbeef0001")
        self.assertEqual(entry.ip_address, "192.0.2.10")
        self.assertEqual(entry.user_agent, "TestClient/1.0")

    def test_x_forwarded_for_preferred_over_remote_addr(self):
        fake_request = _FakeRequest(
            meta={
                "HTTP_X_FORWARDED_FOR": "198.51.100.7, 10.0.0.1",
                "REMOTE_ADDR": "10.0.0.1",
            }
        )

        entry = AuditLogService.record(
            action=AuditAction.CREATE,
            entity_type="role",
            entity_id=uuid.uuid4(),
            request=fake_request,
        )

        self.assertEqual(entry.ip_address, "198.51.100.7")

    def test_missing_request_leaves_context_fields_null(self):
        entry = AuditLogService.record(
            action=AuditAction.CREATE,
            entity_type="role",
            entity_id=uuid.uuid4(),
        )

        self.assertIsNone(entry.request_id)
        self.assertIsNone(entry.ip_address)
        self.assertIsNone(entry.user_agent)

    def test_missing_actor_user_leaves_actor_null(self):
        entry = AuditLogService.record(
            action=AuditAction.CREATE,
            entity_type="role",
            entity_id=uuid.uuid4(),
            actor_user=None,
        )

        self.assertIsNone(entry.actor_user_id)

    def test_repository_exposes_no_update_or_delete(self):
        """
        Append-only enforcement: the repository must not expose any way to
        mutate or remove an existing row.
        """
        from apps.audit.repositories import AuditLogRepository

        self.assertFalse(hasattr(AuditLogRepository, "update"))
        self.assertFalse(hasattr(AuditLogRepository, "delete"))


class ActivityLogServiceTestCase(TestCase):
    """
    Unit tests for ActivityLogService (BE-047).
    """

    def setUp(self):
        self.company = Company.objects.create(name="Studio One")
        self.other_company = Company.objects.create(name="Studio Two")
        self.user = User.objects.create_user(
            email="actor@example.com", name="Actor", password="StrongPassword123!"
        )

    def test_scoped_to_company(self):
        AuditLogService.record(
            action=AuditAction.CREATE, entity_type="role", entity_id=uuid.uuid4(), company_id=self.company.id,
        )
        AuditLogService.record(
            action=AuditAction.CREATE, entity_type="role", entity_id=uuid.uuid4(), company_id=self.other_company.id,
        )

        results = ActivityLogService.list_activity_for_company(self.company.id)
        self.assertEqual(results.count(), 1)

    def test_filter_by_entity_type(self):
        AuditLogService.record(
            action=AuditAction.CREATE, entity_type="role", entity_id=uuid.uuid4(), company_id=self.company.id,
        )
        AuditLogService.record(
            action=AuditAction.CREATE, entity_type="client", entity_id=uuid.uuid4(), company_id=self.company.id,
        )

        results = ActivityLogService.list_activity_for_company(self.company.id, entity_type="client")
        self.assertEqual(results.count(), 1)
        self.assertEqual(results.first().entity_type, "client")

    def test_filter_by_action(self):
        AuditLogService.record(
            action=AuditAction.CREATE, entity_type="role", entity_id=uuid.uuid4(), company_id=self.company.id,
        )
        AuditLogService.record(
            action=AuditAction.DELETE, entity_type="role", entity_id=uuid.uuid4(), company_id=self.company.id,
        )

        results = ActivityLogService.list_activity_for_company(self.company.id, action=AuditAction.DELETE)
        self.assertEqual(results.count(), 1)

    def test_filter_by_actor_user_id(self):
        other_user = User.objects.create_user(
            email="other@example.com", name="Other", password="StrongPassword123!"
        )
        AuditLogService.record(
            action=AuditAction.CREATE, entity_type="role", entity_id=uuid.uuid4(),
            company_id=self.company.id, actor_user=self.user,
        )
        AuditLogService.record(
            action=AuditAction.CREATE, entity_type="role", entity_id=uuid.uuid4(),
            company_id=self.company.id, actor_user=other_user,
        )

        results = ActivityLogService.list_activity_for_company(self.company.id, actor_user_id=self.user.id)
        self.assertEqual(results.count(), 1)
        self.assertEqual(results.first().actor_user_id, self.user.id)
