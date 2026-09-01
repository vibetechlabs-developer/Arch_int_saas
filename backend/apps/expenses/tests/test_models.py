import uuid
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.clients.models import Client
from apps.company.models import Company, CompanyStatus
from apps.expenses.models import Expense, ExpenseApprovalStatus
from apps.projects.models import Project
from apps.users.models import CompanyMembership, CompanyMembershipStatus

User = get_user_model()


class ExpenseModelTestCase(TestCase):
    """
    Unit test suite for Expense domain model (BE-044).
    """

    def setUp(self):
        self.company = Company.objects.create(name="Test Company", status=CompanyStatus.ACTIVE)
        self.client_obj = Client.objects.create(company=self.company, name="Jane Doe")
        self.project = Project.objects.create(
            company=self.company, client=self.client_obj, name="Kitchen Remodel"
        )
        self.user = User.objects.create_user(
            email="employee@example.com", name="An Employee", password="StrongPassword123!"
        )
        CompanyMembership.objects.create(
            company=self.company, user=self.user, status=CompanyMembershipStatus.ACTIVE
        )

    def _create_expense(self, **overrides):
        fields = dict(
            company=self.company,
            project=self.project,
            category="Materials",
            amount=Decimal("500.00"),
            date="2026-09-01",
        )
        fields.update(overrides)
        return Expense.objects.create(**fields)

    def test_expense_creation_defaults(self):
        expense = self._create_expense()
        self.assertIsInstance(expense.id, uuid.UUID)
        self.assertEqual(expense.approval_status, ExpenseApprovalStatus.DRAFT)
        self.assertEqual(expense.tax, 0)
        self.assertIsNone(expense.employee)
        self.assertIsNone(expense.added_by)
        self.assertFalse(expense.is_deleted)

    def test_expense_str_representation(self):
        expense = self._create_expense()
        self.assertEqual(str(expense), f"Materials: 500.00 ({self.project.name})")

    def test_expense_requires_project(self):
        with self.assertRaises(Exception):
            Expense.objects.create(company=self.company, amount=Decimal("1.00"), date="2026-09-01")

    def test_expense_with_employee_and_added_by(self):
        expense = self._create_expense(employee=self.user, added_by=self.user)
        self.assertEqual(expense.employee, self.user)
        self.assertEqual(expense.added_by, self.user)

    def test_expense_employee_set_null_on_user_hard_delete(self):
        expense = self._create_expense(employee=self.user)
        self.user.delete(hard=True)
        expense.refresh_from_db()
        self.assertIsNone(expense.employee)

    def test_expense_cascade_delete_with_project(self):
        expense = self._create_expense()
        expense_id = expense.id
        self.project.delete(hard=True)
        self.assertFalse(Expense.all_objects.filter(id=expense_id).exists())

    def test_expense_soft_delete_lifecycle(self):
        expense = self._create_expense()
        expense_id = expense.id

        expense.delete()
        self.assertTrue(expense.is_deleted)
        self.assertFalse(Expense.objects.filter(id=expense_id).exists())
        self.assertTrue(Expense.all_objects.filter(id=expense_id).exists())

        expense.restore()
        self.assertTrue(Expense.objects.filter(id=expense_id).exists())

    def test_reverse_accessor_from_project(self):
        self._create_expense()
        self.assertEqual(self.project.expenses.count(), 1)
