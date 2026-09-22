"""
BE-069, Phase 8: concurrency safety for the last-active-Owner invariant.

Two concurrent requests, each demoting a DIFFERENT one of a company's two
active Owners, must never both succeed -- exactly one must be rejected,
and the company must end up with at least one active Owner. A naive
"if count == 1: reject" check performed outside a lock is vulnerable to
both requests reading count=2 before either commits; this test forces
that exact race window open deterministically (rather than relying on
incidental thread-scheduling luck) and confirms
CompanyMembershipRepository.lock_active_role_membership_ids's
SELECT ... FOR UPDATE serializes the two transactions correctly.

Uses TransactionTestCase (not TestCase) so each thread gets a real,
separately-committing connection and the database-level row lock is
actually exercised — TestCase's implicit outer transaction-per-test would
prevent a genuine cross-thread lock/commit sequence from ever occurring
(mirrors apps/users/tests/test_role_concurrency.py's own precedent).
"""

import threading
import time
from unittest.mock import patch

from django.db import connection
from django.test import TransactionTestCase

from apps.common.exceptions import ConflictError
from apps.company.services import CompanyService
from apps.users.models import CompanyMembershipStatus, Role, User
from apps.users.repositories import CompanyMembershipRepository
from apps.users.services import CompanyMembershipService


class LastOwnerConcurrencyTestCase(TransactionTestCase):
    def setUp(self):
        self.company, _ = CompanyService.create_company(name="Concurrency Co")
        self.owner_role = Role.objects.get(company=self.company, system_key="owner")
        self.admin_role = Role.objects.get(company=self.company, system_key="admin")

        self.user_a = User.objects.create_user(email="conc-a@example.com", name="Owner A", password="x")
        self.user_b = User.objects.create_user(email="conc-b@example.com", name="Owner B", password="x")
        self.membership_a, _, _ = CompanyMembershipService.add_user(
            self.company.id, "conc-a@example.com", "Owner A", self.owner_role.id
        )
        self.membership_b, _, _ = CompanyMembershipService.add_user(
            self.company.id, "conc-b@example.com", "Owner B", self.owner_role.id
        )

    def tearDown(self):
        connection.close()

    def test_two_concurrent_demotions_of_different_owners_do_not_both_succeed(self):
        """
        Widens the real SELECT ... FOR UPDATE's lock window with a short
        sleep taken *while the lock is held* (inside the same open
        transaction/connection), so the second thread's own
        SELECT ... FOR UPDATE deterministically blocks on the first
        thread's lock rather than possibly racing to completion before
        the other even starts.
        """
        results = []
        original = CompanyMembershipRepository.lock_active_role_membership_ids

        def slow_lock(*args, **kwargs):
            locked_ids = original(*args, **kwargs)
            time.sleep(0.2)
            return locked_ids

        def attempt_demote(membership_id):
            try:
                CompanyMembershipService.assign_role(membership_id, self.admin_role.id)
                results.append(("ok", membership_id))
            except ConflictError as exc:
                results.append(("conflict", exc.code))
            except Exception as exc:  # noqa: BLE001 — must never see an unexpected exception here
                results.append(("unexpected", exc))
            finally:
                connection.close()

        with patch.object(
            CompanyMembershipRepository, "lock_active_role_membership_ids", side_effect=slow_lock
        ):
            t1 = threading.Thread(target=attempt_demote, args=(self.membership_a.id,))
            t2 = threading.Thread(target=attempt_demote, args=(self.membership_b.id,))
            t1.start()
            time.sleep(0.05)  # ensure t1 acquires the lock first, deterministically
            t2.start()
            t1.join()
            t2.join()

        outcomes = [r[0] for r in results]
        self.assertEqual(len(results), 2)
        self.assertEqual(outcomes.count("ok"), 1, f"expected exactly one success, got {results}")
        self.assertEqual(
            outcomes.count("conflict"), 1, f"expected exactly one LAST_OWNER_REQUIRED rejection, got {results}"
        )
        self.assertEqual(outcomes.count("unexpected"), 0, f"unexpected exception type: {results}")

        active_owner_count = CompanyMembershipRepository.all().filter(
            company_id=self.company.id,
            role_id=self.owner_role.id,
            status=CompanyMembershipStatus.ACTIVE,
        ).count()
        self.assertGreaterEqual(
            active_owner_count, 1, "the company must never end up with zero active Owners"
        )
        self.assertEqual(
            active_owner_count, 1, "exactly one owner should have been successfully demoted"
        )
