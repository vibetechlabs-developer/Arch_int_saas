import datetime
import uuid
from typing import Any, Dict, List

from django.utils import timezone

from apps.audit.services import ActivityLogService
from apps.expenses.models import Expense
from apps.invoices.models import Invoice, InvoiceStatus
from apps.invoices.services import InvoiceService
from apps.projects.models import Project, TERMINAL_PROJECT_STATUSES
from apps.quotations.models import Quotation
from apps.reports.services import FinanceReportService

# "Recent" list sizes -- CLAUDE.md's Dashboard section names each section
# but not a page size; 5 is this codebase's existing precedent for a
# dashboard-style recency list (matches BOQSummaryService/reports-style
# "small, fixed" scope rather than a paginated collection). Activities
# gets a slightly larger window since a feed is scanned, not skimmed.
RECENT_LIMIT = 5
ACTIVITY_LIMIT = 10
UPCOMING_DEADLINE_DAYS = 30


class DashboardService:
    """
    `GET /reports/dashboard` (BE-048), per CLAUDE.md's Dashboard / Reports
    section: 8 KPI cards plus 8 "recent" sections. Reuses
    FinanceReportService (BE-045) for every money KPI rather than
    recomputing the same revenue/received/expenses/profit-loss formulas a
    second time, and ActivityLogService (BE-047) for the activity feed --
    pure read-only aggregation, no model/persistence of its own.
    """

    @classmethod
    def compute(cls, company_id: str | uuid.UUID) -> Dict[str, Any]:
        return {
            "kpis": cls._compute_kpis(company_id),
            "recentProjects": cls._recent_projects(company_id),
            "recentQuotations": cls._recent_quotations(company_id),
            "pendingPayments": cls._pending_payments(company_id),
            "overdueInvoices": cls._overdue_invoices(company_id),
            "recentExpenses": cls._recent_expenses(company_id),
            "upcomingDeadlines": cls._upcoming_deadlines(company_id),
            "recentActivities": cls._recent_activities(company_id),
            "projectProfitability": cls._project_profitability(company_id),
        }

    @classmethod
    def _compute_kpis(cls, company_id: str | uuid.UUID) -> Dict[str, Any]:
        finance = FinanceReportService.compute(company_id)

        total_projects = Project.objects.filter(company_id=company_id).count()
        active_projects = (
            Project.objects.filter(company_id=company_id).exclude(status__in=TERMINAL_PROJECT_STATUSES).count()
        )
        total_quotations = (
            Quotation.objects.filter(company_id=company_id).values("quote_number").distinct().count()
        )

        return {
            "totalProjects": total_projects,
            "activeProjects": active_projects,
            "totalQuotations": total_quotations,
            "totalBilledRevenue": finance["revenue"],
            "totalReceived": finance["received"],
            "pendingAmount": finance["receivables"],
            "totalExpenses": finance["expenses"],
            "netProfitLoss": finance["profit_loss"],
        }

    @classmethod
    def _recent_projects(cls, company_id: str | uuid.UUID) -> List[Dict[str, Any]]:
        projects = Project.objects.select_related("client").filter(company_id=company_id).order_by(
            "-created_at", "id"
        )[:RECENT_LIMIT]
        return [
            {
                "id": p.id,
                "name": p.name,
                "status": p.status,
                "clientName": p.client.name,
                "createdAt": p.created_at,
            }
            for p in projects
        ]

    @classmethod
    def _recent_quotations(cls, company_id: str | uuid.UUID) -> List[Dict[str, Any]]:
        quotations = Quotation.objects.select_related("project").filter(company_id=company_id).order_by(
            "-created_at", "id"
        )[:RECENT_LIMIT]
        return [
            {
                "id": q.id,
                "quoteNumber": q.quote_number,
                "version": q.version,
                "status": q.status,
                "total": q.total,
                "projectName": q.project.name,
            }
            for q in quotations
        ]

    @classmethod
    def _pending_payments(cls, company_id: str | uuid.UUID) -> List[Dict[str, Any]]:
        invoices = (
            Invoice.objects.select_related("project")
            .filter(company_id=company_id, status__in=(InvoiceStatus.SENT, InvoiceStatus.PARTIALLY_PAID))
            .order_by("due_date", "id")[:RECENT_LIMIT]
        )
        return [
            {
                "id": inv.id,
                "invoiceNumber": inv.invoice_number,
                "total": inv.total,
                "dueDate": inv.due_date,
                "projectName": inv.project.name,
            }
            for inv in invoices
        ]

    @classmethod
    def _overdue_invoices(cls, company_id: str | uuid.UUID) -> List[Dict[str, Any]]:
        candidates = Invoice.objects.select_related("project").filter(
            company_id=company_id,
            status__in=(InvoiceStatus.SENT, InvoiceStatus.PARTIALLY_PAID),
            due_date__lt=timezone.localdate(),
        ).order_by("due_date", "id")

        overdue = []
        for invoice in candidates:
            if InvoiceService.compute_effective_status(invoice) != InvoiceStatus.OVERDUE:
                continue
            overdue.append(
                {
                    "id": invoice.id,
                    "invoiceNumber": invoice.invoice_number,
                    "total": invoice.total,
                    "dueDate": invoice.due_date,
                    "projectName": invoice.project.name,
                }
            )
            if len(overdue) >= RECENT_LIMIT:
                break

        return overdue

    @classmethod
    def _recent_expenses(cls, company_id: str | uuid.UUID) -> List[Dict[str, Any]]:
        expenses = Expense.objects.select_related("project").filter(company_id=company_id).order_by(
            "-date", "-created_at", "id"
        )[:RECENT_LIMIT]
        return [
            {
                "id": e.id,
                "category": e.category,
                "amount": e.amount,
                "date": e.date,
                "projectName": e.project.name,
            }
            for e in expenses
        ]

    @classmethod
    def _upcoming_deadlines(cls, company_id: str | uuid.UUID) -> List[Dict[str, Any]]:
        today = timezone.localdate()
        horizon = today + datetime.timedelta(days=UPCOMING_DEADLINE_DAYS)
        projects = (
            Project.objects.filter(
                company_id=company_id,
                deadline__isnull=False,
                deadline__gte=today,
                deadline__lte=horizon,
            )
            .exclude(status__in=TERMINAL_PROJECT_STATUSES)
            .order_by("deadline", "id")[:RECENT_LIMIT]
        )
        return [{"id": p.id, "name": p.name, "deadline": p.deadline} for p in projects]

    @classmethod
    def _recent_activities(cls, company_id: str | uuid.UUID) -> List[Any]:
        return list(ActivityLogService.list_activity_for_company(company_id)[:ACTIVITY_LIMIT])

    @classmethod
    def _project_profitability(cls, company_id: str | uuid.UUID) -> List[Dict[str, Any]]:
        active_projects = Project.objects.filter(company_id=company_id).exclude(
            status__in=TERMINAL_PROJECT_STATUSES
        )

        rows = []
        for project in active_projects:
            finance = FinanceReportService.compute(company_id, project_id=project.id)
            rows.append(
                {
                    "projectId": project.id,
                    "projectName": project.name,
                    "revenue": finance["revenue"],
                    "expenses": finance["expenses"],
                    "profit": finance["profit_loss"],
                }
            )

        rows.sort(key=lambda row: row["profit"], reverse=True)
        return rows[:RECENT_LIMIT]
