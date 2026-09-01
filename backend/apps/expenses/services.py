import datetime
import uuid
from decimal import Decimal
from typing import Any, Dict, Optional

from django.db import transaction
from django.db.models import QuerySet
from rest_framework import exceptions as drf_exceptions

from apps.audit.models import AuditAction
from apps.audit.services import AuditLogService
from apps.common.exceptions import ConflictError
from apps.expenses import selectors, validators
from apps.expenses.models import Expense, ExpenseApprovalStatus
from apps.expenses.repositories import ExpenseRepository
from apps.projects.models import Project
from apps.projects.validators import validate_assignee_company_membership

EXPENSE_AUDITED_FIELDS = (
    "project_id",
    "category",
    "vendor",
    "employee_id",
    "amount",
    "tax",
    "date",
    "payment_method",
    "receipt_url",
    "notes",
    "added_by_id",
    "approval_status",
)


def _serialize_expense_audit_value(value: Any) -> Any:
    """
    Same JSONField-has-no-custom-encoder reasoning as
    apps.invoices.services._serialize_invoice_audit_value.
    """
    if isinstance(value, (datetime.date, datetime.datetime)):
        return value.isoformat()
    if isinstance(value, uuid.UUID):
        return str(value)
    if isinstance(value, Decimal):
        return str(value)
    return value


def _expense_audit_state(expense: Expense) -> Dict[str, Any]:
    return {
        field: _serialize_expense_audit_value(getattr(expense, field))
        for field in EXPENSE_AUDITED_FIELDS
    }


class ExpenseService:
    """
    Business logic and orchestration service for Expense management
    (BE-044). Workflow: draft -> submitted -> approved -> paid
    (ExpenseApprovalStatus), matching Finance_API.md's
    submit/approve/mark-paid action endpoints exactly.
    """

    @classmethod
    def list_expenses_for_project(
        cls,
        project: Project,
        category: Optional[str] = None,
        vendor: Optional[str] = None,
        employee_id: Optional[str | uuid.UUID] = None,
        approval_status: Optional[str] = None,
        date_from: Optional[datetime.date] = None,
        date_to: Optional[datetime.date] = None,
        ordering: str = "-date",
    ) -> QuerySet[Expense]:
        return selectors.list_expenses_for_project(
            project.id,
            category=category,
            vendor=vendor,
            employee_id=employee_id,
            approval_status=approval_status,
            date_from=date_from,
            date_to=date_to,
            ordering=ordering,
        )

    @classmethod
    def get_expense_by_id(
        cls,
        expense_id: str | uuid.UUID,
        company_id: Optional[str | uuid.UUID] = None,
    ) -> Expense:
        """
        Retrieve an active, non-deleted Expense by primary key UUID.
        Raises NotFound if it does not exist, is soft-deleted, or belongs
        to another company.
        """
        expense = ExpenseRepository.get_by_id(expense_id)

        if company_id is not None and str(expense.company_id) != str(company_id):
            raise drf_exceptions.NotFound("The requested expense was not found.")

        return expense

    @classmethod
    def create_expense(
        cls,
        project: Project,
        category: str = "",
        vendor: str = "",
        employee_id: Optional[str | uuid.UUID] = None,
        amount: Any = None,
        tax: Any = None,
        date: Any = None,
        payment_method: str = "",
        receipt_url: str = "",
        notes: str = "",
        actor_user: Any = None,
        request: Any = None,
    ) -> Expense:
        """
        Create a new Expense within an already-authorized Project.
        `added_by` is always the acting user (Finance_API.md's own field
        list: "Added By"). `employee`, when supplied, must belong to an
        active CompanyMembership of the project's company -- reuses
        apps.projects.validators.validate_assignee_company_membership, the
        same invariant Project.assigned_to/ProjectMember already enforce.
        Always created at `draft` (Finance_API.md: "Submit expense
        (draft)" is this create endpoint's own documented label; a
        separate `/submit` action is the actual draft -> submitted
        transition).
        """
        with transaction.atomic():
            company = ExpenseRepository.get_company_by_id(project.company_id)
            cleaned_amount = validators.require_positive_amount(amount)

            if date is None:
                raise drf_exceptions.ValidationError({"date": ["date is required."]})

            employee = None
            if employee_id:
                validate_assignee_company_membership(employee_id, project.company_id)
                employee = ExpenseRepository.get_user_by_id(employee_id)

            expense = ExpenseRepository.create(
                company=company,
                project=project,
                category=category or "",
                vendor=vendor or "",
                employee=employee,
                amount=cleaned_amount,
                tax=tax if tax is not None else Decimal("0.00"),
                date=date,
                payment_method=payment_method or "",
                receipt_url=receipt_url or "",
                notes=notes or "",
                added_by=actor_user,
                approval_status=ExpenseApprovalStatus.DRAFT,
            )

            AuditLogService.record(
                action=AuditAction.CREATE,
                entity_type="expense",
                entity_id=expense.id,
                company_id=company.id,
                actor_user=actor_user,
                after_state=_expense_audit_state(expense),
                request=request,
            )

            return expense

    @classmethod
    def update_expense(
        cls,
        expense: Expense,
        category: Optional[str] = None,
        vendor: Optional[str] = None,
        employee_id: Any = "unset",
        amount: Any = None,
        tax: Any = None,
        date: Any = None,
        payment_method: Optional[str] = None,
        receipt_url: Optional[str] = None,
        notes: Optional[str] = None,
        actor_user: Any = None,
        request: Any = None,
    ) -> Expense:
        """
        Edit an already-authorized Expense -- draft only (mirrors
        InvoiceService.update_invoice's identical guard; added for CRUD
        consistency, the same Backend Lead precedent BE-031/BE-035
        established, since Finance_API.md's Expense section documents no
        PATCH of its own). `employee_id` uses the sentinel default
        `"unset"` rather than `None` so an explicit `null` (clear the
        employee) is distinguishable from "not supplied" (leave
        unchanged).
        """
        with transaction.atomic():
            if expense.approval_status != ExpenseApprovalStatus.DRAFT:
                raise ConflictError("Only a draft expense can be edited.")

            before_state = _expense_audit_state(expense)
            fields: Dict[str, Any] = {}

            if category is not None:
                fields["category"] = category
            if vendor is not None:
                fields["vendor"] = vendor
            if amount is not None:
                fields["amount"] = validators.require_positive_amount(amount)
            if tax is not None:
                fields["tax"] = tax
            if date is not None:
                fields["date"] = date
            if payment_method is not None:
                fields["payment_method"] = payment_method
            if receipt_url is not None:
                fields["receipt_url"] = receipt_url
            if notes is not None:
                fields["notes"] = notes

            if employee_id != "unset":
                if employee_id:
                    validate_assignee_company_membership(employee_id, expense.company_id)
                    fields["employee"] = ExpenseRepository.get_user_by_id(employee_id)
                else:
                    fields["employee"] = None

            expense = ExpenseRepository.save(expense, fields)

            AuditLogService.record(
                action=AuditAction.UPDATE,
                entity_type="expense",
                entity_id=expense.id,
                company_id=expense.company_id,
                actor_user=actor_user,
                before_state=before_state,
                after_state=_expense_audit_state(expense),
                request=request,
            )

            return expense

    @classmethod
    def soft_delete_expense(cls, expense: Expense, actor_user: Any = None, request: Any = None) -> None:
        """
        Soft-delete an Expense -- draft only, mirroring update_expense's
        guard (added for CRUD consistency, not documented in
        Finance_API.md).
        """
        with transaction.atomic():
            if expense.approval_status != ExpenseApprovalStatus.DRAFT:
                raise ConflictError("Only a draft expense can be deleted.")

            expense_id = expense.id
            company_id = expense.company_id
            before_state = _expense_audit_state(expense)

            ExpenseRepository.soft_delete(expense)

            AuditLogService.record(
                action=AuditAction.DELETE,
                entity_type="expense",
                entity_id=expense_id,
                company_id=company_id,
                actor_user=actor_user,
                before_state=before_state,
                request=request,
            )

    @classmethod
    def _transition(
        cls,
        expense: Expense,
        from_status: str,
        to_status: str,
        action: AuditAction,
        conflict_message: str,
        actor_user: Any = None,
        request: Any = None,
    ) -> Expense:
        with transaction.atomic():
            if expense.approval_status != from_status:
                raise ConflictError(conflict_message)

            before_state = _expense_audit_state(expense)
            expense = ExpenseRepository.save(expense, {"approval_status": to_status})

            AuditLogService.record(
                action=action,
                entity_type="expense",
                entity_id=expense.id,
                company_id=expense.company_id,
                actor_user=actor_user,
                before_state=before_state,
                after_state=_expense_audit_state(expense),
                request=request,
            )

            return expense

    @classmethod
    def submit_expense(cls, expense: Expense, actor_user: Any = None, request: Any = None) -> Expense:
        """`draft -> submitted` (BE-044)."""
        return cls._transition(
            expense,
            from_status=ExpenseApprovalStatus.DRAFT,
            to_status=ExpenseApprovalStatus.SUBMITTED,
            action=AuditAction.UPDATE,
            conflict_message="Only a draft expense can be submitted.",
            actor_user=actor_user,
            request=request,
        )

    @classmethod
    def approve_expense(cls, expense: Expense, actor_user: Any = None, request: Any = None) -> Expense:
        """`submitted -> approved` (BE-044). Uses AuditAction.APPROVE."""
        return cls._transition(
            expense,
            from_status=ExpenseApprovalStatus.SUBMITTED,
            to_status=ExpenseApprovalStatus.APPROVED,
            action=AuditAction.APPROVE,
            conflict_message="Only a submitted expense can be approved.",
            actor_user=actor_user,
            request=request,
        )

    @classmethod
    def mark_paid_expense(cls, expense: Expense, actor_user: Any = None, request: Any = None) -> Expense:
        """`approved -> paid` (BE-044)."""
        return cls._transition(
            expense,
            from_status=ExpenseApprovalStatus.APPROVED,
            to_status=ExpenseApprovalStatus.PAID,
            action=AuditAction.UPDATE,
            conflict_message="Only an approved expense can be marked paid.",
            actor_user=actor_user,
            request=request,
        )
