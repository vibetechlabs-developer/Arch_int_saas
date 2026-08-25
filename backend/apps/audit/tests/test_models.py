import uuid
from django.test import TestCase

from apps.audit.models import AuditAction, AuditLog
from apps.company.models import Company
from apps.users.models import User


class AuditLogModelTestCase(TestCase):
    """
    Unit tests for the AuditLog model (BE-019).
    """

    def setUp(self):
        self.company = Company.objects.create(name="Audit Test Co")
        self.user = User.objects.create_user(
            email="auditor@example.com", name="Auditor", password="StrongPassword123!"
        )

    def test_create_full_entry(self):
        entry = AuditLog.objects.create(
            company=self.company,
            actor_user=self.user,
            entity_type="role",
            entity_id=uuid.uuid4(),
            action=AuditAction.CREATE,
            before_state=None,
            after_state={"name": "Accountant"},
            request_id="req_abc123def456",
            ip_address="203.0.113.5",
            user_agent="pytest-client/1.0",
        )

        self.assertIsInstance(entry.id, uuid.UUID)
        self.assertEqual(entry.company, self.company)
        self.assertEqual(entry.actor_user, self.user)
        self.assertEqual(entry.action, "create")
        self.assertIsNone(entry.before_state)
        self.assertEqual(entry.after_state, {"name": "Accountant"})
        self.assertIsNotNone(entry.created_at)

    def test_company_and_actor_are_nullable(self):
        """
        Platform-level actions (no company) and system/automated actions
        (no actor) must both be representable.
        """
        entry = AuditLog.objects.create(
            company=None,
            actor_user=None,
            entity_type="company",
            entity_id=uuid.uuid4(),
            action=AuditAction.CREATE,
            after_state={"name": "New Co"},
        )

        self.assertIsNone(entry.company)
        self.assertIsNone(entry.actor_user)

    def test_company_hard_delete_sets_null_not_cascade(self):
        """
        The audit row must outlive the tenant record it concerns — a hard
        company delete must SET_NULL on audit_log.company_id, never cascade
        the audit entry itself out of existence.
        """
        entry = AuditLog.objects.create(
            company=self.company,
            entity_type="company",
            entity_id=self.company.id,
            action=AuditAction.CREATE,
            after_state={"name": self.company.name},
        )

        self.company.hard_delete()
        entry.refresh_from_db()

        self.assertIsNone(entry.company_id)

    def test_ordering_is_newest_first(self):
        from datetime import timedelta
        from django.utils import timezone

        older = AuditLog.objects.create(
            entity_type="role", entity_id=uuid.uuid4(), action=AuditAction.CREATE
        )
        newer = AuditLog.objects.create(
            entity_type="role", entity_id=uuid.uuid4(), action=AuditAction.CREATE
        )
        # auto_now_add can give both rows the same timestamp at test speed;
        # force a deterministic, distinct ordering via a direct queryset
        # update (bypasses auto_now_add, which only applies on INSERT).
        AuditLog.objects.filter(id=older.id).update(
            created_at=timezone.now() - timedelta(minutes=1)
        )

        entries = list(AuditLog.objects.all())
        self.assertEqual(entries[0].id, newer.id)
        self.assertEqual(entries[1].id, older.id)

    def test_str_representation(self):
        entry = AuditLog.objects.create(
            entity_type="role", entity_id=uuid.uuid4(), action=AuditAction.UPDATE
        )
        self.assertIn("update", str(entry))
        self.assertIn("role", str(entry))
