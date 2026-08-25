# Finance API (Draft)
## INT Projects — Multi-Company Interior & Architecture Management SaaS

**Status:** Draft endpoint sketch.

---

## Scope

Quotation, Contract, Invoice, Payment, Expense, and Reports — the financial lifecycle of a project. All endpoints require, at minimum, `financial.view`-tier permissions; mutating endpoints require the specific action permission per role (see `05_Security/Permissions.md`).

## Quotation

| Method | Path | Purpose |
|---|---|---|
| GET | `/companies/{companyId}/projects/{projectId}/quotations` | List quotations (all versions) |
| POST | `/companies/{companyId}/projects/{projectId}/quotations` | Create quotation (optionally from BOQ) |
| GET | `/companies/{companyId}/quotations/{quotationId}` | Get quotation detail |
| POST | `/companies/{companyId}/quotations/{quotationId}/revise` | Create new version (revision) |
| POST | `/companies/{companyId}/quotations/{quotationId}/send` | Mark sent to client |
| POST | `/companies/{companyId}/quotations/{quotationId}/approve` | Record client approval |
| POST | `/companies/{companyId}/quotations/{quotationId}/reject` | Record rejection/revision request |

## Contract

| Method | Path | Purpose |
|---|---|---|
| POST | `/companies/{companyId}/quotations/{quotationId}/generate-contract` | Generate contract from an approved quotation |
| GET | `/companies/{companyId}/contracts/{contractId}` | Get contract |
| POST | `/companies/{companyId}/contracts/{contractId}/accept` | Record client acceptance |

## Invoice

| Method | Path | Purpose |
|---|---|---|
| GET | `/companies/{companyId}/projects/{projectId}/invoices` | List invoices |
| POST | `/companies/{companyId}/projects/{projectId}/invoices` | Create invoice (from contract/approved quotation, or ad hoc) |
| GET | `/companies/{companyId}/invoices/{invoiceId}` | Get invoice detail (items, status, payments) |
| POST | `/companies/{companyId}/invoices/{invoiceId}/send` | Mark sent to client |
| PATCH | `/companies/{companyId}/invoices/{invoiceId}` | Edit (draft only) |
| POST | `/companies/{companyId}/invoices/{invoiceId}/cancel` | Cancel invoice |

## Payment

| Method | Path | Purpose |
|---|---|---|
| GET | `/companies/{companyId}/invoices/{invoiceId}/payments` | List payments against an invoice |
| POST | `/companies/{companyId}/invoices/{invoiceId}/payments` | Record a payment (date, amount, method, reference, receipt) |
| DELETE | `/companies/{companyId}/payments/{paymentId}` | Void a payment (audit-logged, not hard-deleted) |

## Expense

| Method | Path | Purpose |
|---|---|---|
| GET | `/companies/{companyId}/projects/{projectId}/expenses` | List expenses (filter: category, vendor, employee, date) |
| POST | `/companies/{companyId}/projects/{projectId}/expenses` | Submit expense (draft) |
| POST | `/companies/{companyId}/expenses/{expenseId}/submit` | Draft → Submitted |
| POST | `/companies/{companyId}/expenses/{expenseId}/approve` | Submitted → Approved |
| POST | `/companies/{companyId}/expenses/{expenseId}/mark-paid` | Approved → Paid |

## Reports

| Method | Path | Purpose |
|---|---|---|
| GET | `/companies/{companyId}/reports/dashboard` | KPI cards (projects, quotations, revenue, received, pending, expenses, profit/loss) |
| GET | `/companies/{companyId}/reports/sales` | Leads, quotations, approval/rejection, conversion rate |
| GET | `/companies/{companyId}/reports/projects` | Active/completed/delayed, progress, profitability |
| GET | `/companies/{companyId}/reports/finance` | Revenue, received, outstanding, expenses, P&L, receivables |
| GET | `/companies/{companyId}/reports/expenses` | Category-wise, project-wise, vendor-wise, employee-wise, date-wise |

All report endpoints accept `?dateFrom=&dateTo=&projectId=` query filters per the source requirement's "Date filtering / Project filtering."

## Notes

- Invoice status (`Draft/Sent/Partially Paid/Paid/Overdue/Cancelled`) is derived server-side from paid-vs-total amount and due date — never client-settable directly except through the explicit action endpoints above.
- Every mutating endpoint on this page (quotation approve/reject, invoice send/cancel, payment record/void, expense approve) must write an `audit_log` entry per `01_Business/FRS.md` §27.
- Quotation revision creates a new row/version rather than mutating the sent version, per the source requirement's explicit versioning rule.
