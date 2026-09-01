import datetime
import uuid
from decimal import Decimal
from typing import Any, Dict, List, Optional

from django.db.models import Sum
from django.utils import timezone

from apps.expenses.models import Expense, ExpenseApprovalStatus
from apps.invoices.models import Invoice, InvoiceStatus
from apps.invoices.services import InvoiceService
from apps.payments.models import Payment
from apps.payments.repositories import PaymentRepository

# Statuses counted as "billed" revenue -- excludes draft (not yet sent to
# the client, so not really revenue yet) and cancelled (never collected).
BILLED_INVOICE_STATUSES = (InvoiceStatus.SENT, InvoiceStatus.PARTIALLY_PAID, InvoiceStatus.PAID)

# Expense statuses counted as actual incurred cost for P&L purposes
# (Backend Lead decision, Sprint 6 planning) -- draft/submitted expenses
# are not yet a confirmed committed cost.
INCURRED_EXPENSE_STATUSES = (ExpenseApprovalStatus.APPROVED, ExpenseApprovalStatus.PAID)


def _zero() -> Decimal:
    return Decimal("0.00")


class FinanceReportService:
    """
    `GET /reports/finance` (BE-045) -- revenue, received, outstanding,
    expenses, P&L, receivables, per Finance_API.md. Pure read-only
    aggregation, no persistence of its own.

    Each figure is scoped independently by its own most natural date
    field (Backend Lead decision, Sprint 6 planning -- Finance_API.md's
    `?dateFrom=&dateTo=` note doesn't name a single unified date column,
    and Invoice/Payment/Expense each already have their own): Invoice by
    `created_at`, Payment by `payment_date`, Expense by `date`.

    Definitions:
    - `revenue`: sum of `total` across every billed (sent/partially_paid/
      paid) invoice in scope -- accrual, not cash.
    - `received`: sum of every active (non-voided) payment amount in
      scope, regardless of its invoice's current status (money already
      collected stays collected even if the invoice is later cancelled).
    - `receivables`: `revenue - received` -- the total unpaid balance
      across every billed invoice in scope, due or not.
    - `outstanding`: the narrower subset of `receivables` that is also
      currently overdue (uses InvoiceService.compute_effective_status,
      the same read-time `overdue` derivation BE-042 established).
    - `expenses`: sum of `amount + tax` across every approved/paid expense
      in scope -- see INCURRED_EXPENSE_STATUSES.
    - `profitLoss`: `revenue - expenses`.
    """

    @classmethod
    def compute(
        cls,
        company_id: str | uuid.UUID,
        project_id: Optional[str | uuid.UUID] = None,
        date_from: Optional[datetime.date] = None,
        date_to: Optional[datetime.date] = None,
    ) -> Dict[str, Decimal]:
        invoice_qs = Invoice.objects.filter(company_id=company_id, status__in=BILLED_INVOICE_STATUSES)
        payment_qs = Payment.objects.filter(company_id=company_id)
        expense_qs = Expense.objects.filter(company_id=company_id, approval_status__in=INCURRED_EXPENSE_STATUSES)

        if project_id:
            invoice_qs = invoice_qs.filter(project_id=project_id)
            payment_qs = payment_qs.filter(project_id=project_id)
            expense_qs = expense_qs.filter(project_id=project_id)

        if date_from:
            invoice_qs = invoice_qs.filter(created_at__date__gte=date_from)
            payment_qs = payment_qs.filter(payment_date__gte=date_from)
            expense_qs = expense_qs.filter(date__gte=date_from)
        if date_to:
            invoice_qs = invoice_qs.filter(created_at__date__lte=date_to)
            payment_qs = payment_qs.filter(payment_date__lte=date_to)
            expense_qs = expense_qs.filter(date__lte=date_to)

        revenue = invoice_qs.aggregate(total=Sum("total"))["total"] or _zero()
        received = payment_qs.aggregate(total=Sum("amount"))["total"] or _zero()
        receivables = revenue - received

        expense_amount = expense_qs.aggregate(total=Sum("amount"))["total"] or _zero()
        expense_tax = expense_qs.aggregate(total=Sum("tax"))["total"] or _zero()
        expenses = expense_amount + expense_tax

        outstanding = cls._compute_outstanding(invoice_qs)

        return {
            "revenue": revenue,
            "received": received,
            "receivables": receivables,
            "outstanding": outstanding,
            "expenses": expenses,
            "profit_loss": revenue - expenses,
        }

    @classmethod
    def _compute_outstanding(cls, invoice_qs) -> Decimal:
        """
        Sum of `total - paid` across every invoice in `invoice_qs` whose
        *effective* status (InvoiceService.compute_effective_status) is
        `overdue`. Narrowed at the DB level first (only sent/
        partially_paid with a past due_date can ever be overdue) before
        the per-invoice paid-total lookup, keeping this a small loop over
        genuine overdue candidates rather than every invoice in scope.
        """
        candidates = invoice_qs.filter(
            status__in=(InvoiceStatus.SENT, InvoiceStatus.PARTIALLY_PAID),
            due_date__lt=timezone.localdate(),
        )

        outstanding = _zero()
        for invoice in candidates:
            if InvoiceService.compute_effective_status(invoice) != InvoiceStatus.OVERDUE:
                continue
            paid_total = PaymentRepository.sum_active_amount_for_invoice(invoice.id)
            outstanding += invoice.total - paid_total

        return outstanding


class ExpenseReportService:
    """
    `GET /reports/expenses` (BE-045) -- category-wise, project-wise,
    vendor-wise, employee-wise, date-wise breakdowns, per Finance_API.md.
    Includes every non-deleted expense in scope regardless of
    approval_status (a broader visibility report, distinct in purpose
    from FinanceReportService's approved/paid-only P&L expense figure).
    """

    @classmethod
    def compute(
        cls,
        company_id: str | uuid.UUID,
        project_id: Optional[str | uuid.UUID] = None,
        date_from: Optional[datetime.date] = None,
        date_to: Optional[datetime.date] = None,
    ) -> Dict[str, List[Dict[str, Any]]]:
        queryset = Expense.objects.filter(company_id=company_id)

        if project_id:
            queryset = queryset.filter(project_id=project_id)
        if date_from:
            queryset = queryset.filter(date__gte=date_from)
        if date_to:
            queryset = queryset.filter(date__lte=date_to)

        return {
            "byCategory": cls._group_by(queryset, "category"),
            "byProject": cls._group_by(queryset, "project_id", label_field="project__name"),
            "byVendor": cls._group_by(queryset, "vendor"),
            "byEmployee": cls._group_by(queryset, "employee_id", label_field="employee__name"),
            "byDate": cls._group_by(queryset, "date"),
        }

    @classmethod
    def _group_by(cls, queryset, key_field: str, label_field: Optional[str] = None) -> List[Dict[str, Any]]:
        values_fields = [key_field] if label_field is None else [key_field, label_field]
        rows = (
            queryset.values(*values_fields)
            .annotate(total=Sum("amount"))
            .order_by(key_field)
        )

        results = []
        for row in rows:
            key = row[key_field]
            entry = {
                "key": str(key) if key is not None else None,
                "label": row.get(label_field) if label_field else key,
                "total": row["total"] or _zero(),
            }
            results.append(entry)
        return results
