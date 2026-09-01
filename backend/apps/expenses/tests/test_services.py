from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import exceptions as drf_exceptions

from apps.clients.models import Client
from apps.common.exceptions import ConflictError
from apps.company.models import Company, CompanyStatus
from apps.expenses.models import ExpenseApprovalStatus
from apps.expenses.services import ExpenseService
from apps.projects.models import Project
from apps.users.models import CompanyMembership, CompanyMembershipStatus

User = get_user_model()


class ExpenseServiceCreateTestCase(TestCase):
    """
    Unit test suite for ExpenseService.create_expense (BE-044).
    """

    def setUp(self):
        self.company = Company.objects.create(name="Studio One", status=CompanyStatus.ACTIVE)
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

    def test_create_expense_defaults_to_draft(self):
        expense = ExpenseService.create_expense(
            project=self.project, category="Materials", amount=Decimal("500.00"), date="2026-09-01",
            actor_user=self.user,
        )
        self.assertEqual(expense.approval_status, ExpenseApprovalStatus.DRAFT)
        self.assertEqual(expense.added_by, self.user)

    def test_create_expense_with_employee(self):
        expense = ExpenseService.create_expense(
            project=self.project, amount=Decimal("100.00"), date="2026-09-01", employee_id=self.user.id,
        )
        self.assertEqual(expense.employee, self.user)

    def test_create_expense_employee_from_another_company_raises_validation_error(self):
        other_company = Company.objects.create(name="Studio Two", status=CompanyStatus.ACTIVE)
        other_user = User.objects.create_user(
            email="other@example.com", name="Other", password="StrongPassword123!"
        )
        CompanyMembership.objects.create(
            company=other_company, user=other_user, status=CompanyMembershipStatus.ACTIVE
        )
        with self.assertRaises(drf_exceptions.ValidationError):
            ExpenseService.create_expense(
                project=self.project, amount=Decimal("100.00"), date="2026-09-01", employee_id=other_user.id,
            )

    def test_create_expense_missing_amount_raises_value_error(self):
        with self.assertRaises(ValueError):
            ExpenseService.create_expense(project=self.project, date="2026-09-01")

    def test_create_expense_zero_amount_raises_value_error(self):
        with self.assertRaises(ValueError):
            ExpenseService.create_expense(project=self.project, amount=Decimal("0.00"), date="2026-09-01")

    def test_create_expense_missing_date_raises_validation_error(self):
        with self.assertRaises(drf_exceptions.ValidationError):
            ExpenseService.create_expense(project=self.project, amount=Decimal("100.00"))

    def test_create_expense_tax_defaults_to_zero(self):
        expense = ExpenseService.create_expense(
            project=self.project, amount=Decimal("100.00"), date="2026-09-01"
        )
        self.assertEqual(expense.tax, Decimal("0.00"))


class ExpenseServiceUpdateAndDeleteTestCase(TestCase):
    """
    Unit test suite for ExpenseService.update_expense/soft_delete_expense
    (BE-044).
    """

    def setUp(self):
        self.company = Company.objects.create(name="Studio One", status=CompanyStatus.ACTIVE)
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
        self.expense = ExpenseService.create_expense(
            project=self.project, category="Materials", amount=Decimal("500.00"), date="2026-09-01",
        )

    def test_update_draft_expense(self):
        updated = ExpenseService.update_expense(self.expense, category="Labour", amount=Decimal("600.00"))
        self.assertEqual(updated.category, "Labour")
        self.assertEqual(updated.amount, Decimal("600.00"))

    def test_update_employee_id_omitted_leaves_unchanged(self):
        ExpenseService.update_expense(self.expense, employee_id=self.user.id)
        self.expense.refresh_from_db()
        self.assertEqual(self.expense.employee, self.user)

        ExpenseService.update_expense(self.expense, category="Labour")
        self.expense.refresh_from_db()
        self.assertEqual(self.expense.employee, self.user)

    def test_update_employee_id_explicit_null_clears_it(self):
        ExpenseService.update_expense(self.expense, employee_id=self.user.id)
        self.expense.refresh_from_db()

        ExpenseService.update_expense(self.expense, employee_id=None)
        self.expense.refresh_from_db()
        self.assertIsNone(self.expense.employee)

    def test_update_non_draft_expense_raises_conflict(self):
        ExpenseService.submit_expense(self.expense)
        self.expense.refresh_from_db()
        with self.assertRaises(ConflictError):
            ExpenseService.update_expense(self.expense, category="Too late")

    def test_soft_delete_draft_expense(self):
        expense_id = self.expense.id
        ExpenseService.soft_delete_expense(self.expense)
        self.assertFalse(ExpenseService.list_expenses_for_project(self.project).filter(id=expense_id).exists())

    def test_soft_delete_non_draft_expense_raises_conflict(self):
        ExpenseService.submit_expense(self.expense)
        self.expense.refresh_from_db()
        with self.assertRaises(ConflictError):
            ExpenseService.soft_delete_expense(self.expense)


class ExpenseServiceApprovalWorkflowTestCase(TestCase):
    """
    Unit test suite for ExpenseService.submit_expense/approve_expense/
    mark_paid_expense (BE-044).
    """

    def setUp(self):
        self.company = Company.objects.create(name="Studio One", status=CompanyStatus.ACTIVE)
        self.client_obj = Client.objects.create(company=self.company, name="Jane Doe")
        self.project = Project.objects.create(
            company=self.company, client=self.client_obj, name="Kitchen Remodel"
        )
        self.expense = ExpenseService.create_expense(
            project=self.project, amount=Decimal("500.00"), date="2026-09-01",
        )

    def test_full_workflow(self):
        submitted = ExpenseService.submit_expense(self.expense)
        self.assertEqual(submitted.approval_status, ExpenseApprovalStatus.SUBMITTED)

        approved = ExpenseService.approve_expense(submitted)
        self.assertEqual(approved.approval_status, ExpenseApprovalStatus.APPROVED)

        paid = ExpenseService.mark_paid_expense(approved)
        self.assertEqual(paid.approval_status, ExpenseApprovalStatus.PAID)

    def test_approve_before_submit_raises_conflict(self):
        with self.assertRaises(ConflictError):
            ExpenseService.approve_expense(self.expense)

    def test_mark_paid_before_approve_raises_conflict(self):
        ExpenseService.submit_expense(self.expense)
        self.expense.refresh_from_db()
        with self.assertRaises(ConflictError):
            ExpenseService.mark_paid_expense(self.expense)

    def test_submit_twice_raises_conflict(self):
        ExpenseService.submit_expense(self.expense)
        self.expense.refresh_from_db()
        with self.assertRaises(ConflictError):
            ExpenseService.submit_expense(self.expense)


class ExpenseServiceListAndGetTestCase(TestCase):
    """
    Unit test suite for ExpenseService.list_expenses_for_project filters
    and get_expense_by_id (BE-044).
    """

    def setUp(self):
        self.company = Company.objects.create(name="Studio One", status=CompanyStatus.ACTIVE)
        self.client_obj = Client.objects.create(company=self.company, name="Jane Doe")
        self.project = Project.objects.create(
            company=self.company, client=self.client_obj, name="Kitchen Remodel"
        )
        self.materials = ExpenseService.create_expense(
            project=self.project, category="Materials", vendor="ABC Corp",
            amount=Decimal("500.00"), date="2026-09-01",
        )
        self.labour = ExpenseService.create_expense(
            project=self.project, category="Labour", vendor="XYZ Corp",
            amount=Decimal("300.00"), date="2026-09-15",
        )

    def test_filter_by_category(self):
        results = ExpenseService.list_expenses_for_project(self.project, category="Materials")
        self.assertEqual(list(results), [self.materials])

    def test_filter_by_vendor(self):
        results = ExpenseService.list_expenses_for_project(self.project, vendor="XYZ Corp")
        self.assertEqual(list(results), [self.labour])

    def test_filter_by_date_range(self):
        results = ExpenseService.list_expenses_for_project(
            self.project, date_from="2026-09-10", date_to="2026-09-30"
        )
        self.assertEqual(list(results), [self.labour])

    def test_filter_by_approval_status(self):
        ExpenseService.submit_expense(self.materials)
        results = ExpenseService.list_expenses_for_project(
            self.project, approval_status=ExpenseApprovalStatus.SUBMITTED
        )
        self.assertEqual(list(results), [self.materials])

    def test_get_by_id_cross_tenant_raises_not_found(self):
        other_company = Company.objects.create(name="Studio Two", status=CompanyStatus.ACTIVE)
        with self.assertRaises(drf_exceptions.NotFound):
            ExpenseService.get_expense_by_id(self.materials.id, company_id=other_company.id)
