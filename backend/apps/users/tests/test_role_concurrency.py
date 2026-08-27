import threading
import time
from unittest.mock import patch

from django.db import connection
from django.test import TransactionTestCase

from apps.common.exceptions import ConflictError
from apps.company.models import Company, CompanyStatus
from apps.users.models import Role
from apps.users.repositories import RoleRepository
from apps.users.services import RoleService


class RoleCreationConcurrencyTestCase(TransactionTestCase):
    """
    RoleService.create_role()/update_role() pre-check name uniqueness via
    RoleRepository.name_exists_for_company() before inserting/saving — a
    classic TOCTOU race under concurrent requests, since two callers can
    both pass the check before either commits. The database's
    unique_active_role_per_company constraint (apps/users/models.py) is the
    real backstop; these tests force the race window open deterministically
    (rather than relying on incidental thread-scheduling luck) and confirm
    the resulting IntegrityError is caught and converted to ConflictError
    (409), not left to propagate as an unhandled 500, and that exactly one
    row survives either way.

    Uses TransactionTestCase (not TestCase) so each thread gets a real,
    separately-committing connection — TestCase's implicit outer
    transaction-per-test would prevent a genuine cross-thread constraint
    violation from ever occurring.
    """

    def setUp(self):
        self.company = Company.objects.create(name="Race Co", status=CompanyStatus.ACTIVE)

    def tearDown(self):
        connection.close()

    def test_concurrent_create_same_role_name_raises_conflict_not_integrity_error(self):
        """
        Both threads' pre-checks are forced to see "no conflict yet" (via a
        patched name_exists_for_company that always returns False after a
        short delay, simulating the exact TOCTOU window), then both attempt
        the real insert. Exactly one must succeed; the other must raise
        ConflictError (409-mappable), never a raw IntegrityError, and the
        database must end up with exactly one row.
        """
        results = []

        def delayed_no_conflict(*args, **kwargs):
            time.sleep(0.05)
            return False

        def attempt_create():
            try:
                role = RoleService.create_role(company_id=self.company.id, name="Racer")
                results.append(("ok", role.id))
            except ConflictError as exc:
                results.append(("conflict", exc))
            except Exception as exc:  # noqa: BLE001 — must never see a raw IntegrityError here
                results.append(("unexpected", exc))
            finally:
                connection.close()

        with patch.object(
            RoleRepository, "name_exists_for_company", side_effect=delayed_no_conflict
        ):
            t1 = threading.Thread(target=attempt_create)
            t2 = threading.Thread(target=attempt_create)
            t1.start()
            t2.start()
            t1.join()
            t2.join()

        outcomes = [r[0] for r in results]
        self.assertEqual(len(results), 2)
        self.assertEqual(outcomes.count("ok"), 1, f"expected exactly one success, got {results}")
        self.assertEqual(
            outcomes.count("conflict"), 1, f"expected exactly one ConflictError, got {results}"
        )
        self.assertEqual(outcomes.count("unexpected"), 0, f"unexpected exception type: {results}")

        self.assertEqual(
            Role.objects.filter(company=self.company, name="Racer").count(),
            1,
            "database uniqueness must hold regardless of the race outcome",
        )

    def test_concurrent_rename_to_same_name_raises_conflict_not_integrity_error(self):
        """
        Same race, but for update_role()'s rename path: two existing roles
        are concurrently renamed to the same target name.
        """
        role_a = Role.objects.create(company=self.company, name="Role A", is_active=True)
        role_b = Role.objects.create(company=self.company, name="Role B", is_active=True)

        results = []

        def delayed_no_conflict(*args, **kwargs):
            time.sleep(0.05)
            return False

        def attempt_rename(role_id):
            try:
                RoleService.update_role(role_id=role_id, validated_data={"name": "Renamed"})
                results.append(("ok", role_id))
            except ConflictError as exc:
                results.append(("conflict", exc))
            except Exception as exc:  # noqa: BLE001
                results.append(("unexpected", exc))
            finally:
                connection.close()

        with patch.object(
            RoleRepository, "name_exists_for_company", side_effect=delayed_no_conflict
        ):
            t1 = threading.Thread(target=attempt_rename, args=(role_a.id,))
            t2 = threading.Thread(target=attempt_rename, args=(role_b.id,))
            t1.start()
            t2.start()
            t1.join()
            t2.join()

        outcomes = [r[0] for r in results]
        self.assertEqual(outcomes.count("ok"), 1, f"expected exactly one success, got {results}")
        self.assertEqual(
            outcomes.count("conflict"), 1, f"expected exactly one ConflictError, got {results}"
        )
        self.assertEqual(outcomes.count("unexpected"), 0, f"unexpected exception type: {results}")

        self.assertEqual(
            Role.objects.filter(company=self.company, name="Renamed").count(),
            1,
            "database uniqueness must hold regardless of the race outcome",
        )
