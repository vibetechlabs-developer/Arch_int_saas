# Test Case Plan (Draft Outline)
## INT Projects — Multi-Company Interior & Architecture Management SaaS

**Status:** Draft outline of required test categories, derived from the functional/business requirements. Detailed step-by-step test cases pending actual UI/API implementation.

---

## 1. Tenant Isolation (highest priority — see `05_Security/Tenant.md`)

- User authenticated for Company A cannot read/write any resource (client, project, quotation, invoice, payment, expense) belonging to Company B, even by guessing/enumerating a valid ID → expect 403/404, never data leakage.
- A request with a `companyId` in the path that doesn't match the caller's active membership is rejected.
- Two companies with identically-named clients/projects never collide or merge in search/list results.
- Report/dashboard endpoints never aggregate figures across companies.

## 2. Authentication & Session

- Login with valid/invalid credentials.
- Password reset flow (token expiry, single-use token).
- Session/token expiry forces re-authentication; refresh flow works and old refresh tokens are invalidated on rotation.
- Platform Super Admin login cannot be used against company-scoped endpoints and vice versa.

## 3. Roles & Permissions

- Each default role (Owner/Admin/PM/Designer/Accountant/Sales) can perform only its documented actions (`05_Security/Permissions.md` §3) — spot-check both the allowed and a deliberately-forbidden action per role.
- Revoking a role/permission takes effect on the next request (not just next login), per the no-embedded-permissions design in `05_Security/JWT.md`.
- Financial-access permission is independently testable from general project view (e.g. Designer sees project but not margins).

## 4. Client Management

- Create/edit/list client; Client 360 view aggregates correct projects/quotations/invoices/payments/documents for that client only.
- Cannot delete a client with active projects (or requires explicit force confirmation).

## 5. Project Lifecycle

- Status transitions follow the allowed lifecycle graph (`Draft → ... → Completed`, plus On Hold/Cancelled); an invalid transition (e.g. Draft → Completed directly) is rejected.
- Project cost-summary reflects live Expense + Invoice/Payment data (create an expense, confirm cost-summary updates immediately).

## 6. BOQ

- `Amount = Quantity × Rate` computed correctly, including with discount/tax applied.
- Optional/alternative items excluded from default total but retrievable separately.

## 7. Quotation

- Quotation total matches sum of line items minus discount plus tax.
- Revising a sent quotation creates a new version rather than mutating the original (version history preserved).
- Quotation cannot be approved twice, or approved after rejection without a new version.

## 8. Invoice & Payment

- Invoice status auto-transitions correctly: Draft → Sent → Partially Paid (after a partial payment) → Paid (after full payment) → Overdue (past due date, unpaid).
- Multiple partial payments sum correctly against invoice total; overpayment is rejected or flagged.
- Voiding a payment updates invoice status and is captured in the audit log, not hard-deleted.

## 9. Expense

- Workflow enforced: Draft → Submitted → Approved → Paid (cannot skip states, e.g. Draft → Paid directly).
- Expense correctly rolls up into project cost by category (materials/labour/vendor/other).

## 10. Reports & Dashboard

- KPI cards (Total Projects, Active Projects, Total Quotations, Billed, Received, Pending, Expenses, Net Profit/Loss) match manually-computed values from underlying transactional records.
- Date-range and project filters correctly scope every report group (Sales/Projects/Finance/Expenses).

## 11. Audit Trail

- Every mutation on invoices, payments, expenses, quotations, permissions, and project changes produces an `audit_log` row with correct old/new values, actor, and timestamp.

## 12. File/Document Storage

- Uploaded documents are tagged with the correct company/project/version and are not retrievable by users outside that company.
- Design version history (Phase 3) is append-only — uploading a new version never overwrites/loses the previous one.

---

See `08_QA/UAT.md` for client-facing acceptance criteria derived from these categories.
