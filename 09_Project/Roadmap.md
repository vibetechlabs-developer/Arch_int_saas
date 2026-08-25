# Roadmap
## INT Projects — Multi-Company Interior & Architecture Management SaaS

**Status:** Draft — phase sequencing derived directly from the source requirements document's MVP Scope section. Timelines (dates/durations) are not yet estimated — to be added once team size and stack are confirmed.

---

## Phase 0 — Requirement Approval Gate (must complete before any build)

- Sign off business flow, user types, company/tenant model, role/permission model
- Sign off project lifecycle, financial lifecycle, BOQ structure
- Sign off quotation/invoice/payment/expense lifecycles
- Sign off reporting definitions and client portal scope
- Source: `01_Business/BRS.md` §9, source doc §36 "What Should NOT Be Done Yet"

## Phase 1 — Foundation

- Authentication
- Multi-company (tenant model + isolation)
- Company profile
- Users
- Roles
- Permissions
- Subscription foundation
- Audit log

**Exit criteria:** a company can be created, users invited with roles, and every write/read is verifiably tenant-scoped (see `08_QA/Test_Cases.md` §1).

## Phase 2 — Current Business Modules (core MVP)

- Dashboard
- Clients
- Projects
- Products / Categories / Subcategories
- BOQ
- Quotations
- Invoices
- Payments
- Expenses
- Reports

**Exit criteria:** the full Client → Project → BOQ → Quotation → Invoice → Payment → Expense → Profitability → Reports loop works end-to-end for a single company (UAT scenarios 2–5 in `08_QA/UAT.md`).

## Phase 3 — Interior Workflow

- Leads
- Site Visits
- Design Management
- Drawing/Revisions
- Approvals
- Tasks
- Project milestones
- Documents

## Phase 4 — Execution

- Vendors
- Procurement
- Purchase Orders
- Inventory
- Site Management
- Labour
- Daily Logs
- Snags
- Handover

## Phase 5 — Advanced SaaS

- Client Portal
- Employee Portal
- Notifications
- WhatsApp integration
- Advanced Analytics
- Subscription Billing
- Usage Limits
- Feature Flags

---

## Sequencing Notes

- Phases 1–2 are the MVP; Phases 3–5 are explicitly deferred per the client's own phasing in the source requirements.
- Do not pull Phase 3+ features forward without client confirmation — the source doc is explicit that "before coding the complete system, do not immediately build every screen."
- `03_Database/Database_Schema.md` and `02_Architecture/LLD.md` should stay scoped to Phase 1–2 tables until Phase 3 is scheduled, to avoid speculative schema that has to be reworked.

See `09_Project/Sprint_Planning.md` for breakdown into executable sprints (pending team/velocity input) and `09_Project/Risk_Register.md` for delivery risks.
