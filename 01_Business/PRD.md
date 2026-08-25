# Product Requirements Document (PRD)
## INT Projects — Multi-Company Interior & Architecture Management SaaS

**Status:** Draft — pending approval
**Source:** `INT_Projects_Client_Requirements_and_Business_Flow.md`

---

## 1. Product Vision

A centralized, multi-tenant business management platform for interior design companies, contractors, architecture firms, turnkey project companies, and furniture/interior execution businesses — connecting client acquisition, project delivery, commercial documents, and financial outcomes in one system.

## 2. Product Type

Multi-Company (multi-tenant) Interior & Architecture Management SaaS.

## 3. Personas & Representative User Stories

**Company Owner**
- "As a Company Owner, I want to see total revenue, receivables, and profit across all my projects so I know the health of my business at a glance."

**Company Admin**
- "As a Company Admin, I want to invite users and assign them roles so I control who can see financial data."

**Project Manager**
- "As a Project Manager, I want to see all my assigned projects with status and deadlines so I know what needs attention today."

**Designer/Architect**
- "As a Designer, I want to upload a new design version and route it for client approval so revisions are tracked, not lost in email threads."

**Accountant**
- "As an Accountant, I want to convert an approved quotation into an invoice and record partial payments so I always know the outstanding balance per client."

**Sales/CRM User**
- "As a Sales user, I want to log a site visit against a lead and convert it to a client and project once won."

**Client (future portal)**
- "As a Client, I want to view and approve my quotation and see my payment status online, without seeing internal costs or other clients' data."

**Platform Super Admin**
- "As the Platform Super Admin, I want to see all companies and their subscription status without being able to browse into their business data casually — access should be explicit and audited."

## 4. Product Principles

1. Multi-company isolation is foundational, not bolted on.
2. Project is the central operational entity; Client is the central commercial entity.
3. BOQ bridges product/work catalog to quotation; Quotation bridges to commercial agreement; Invoice/Payment is the financial lifecycle.
4. Reports are derived from live transactional data — never a separately maintained number.
5. Anything sensitive (financial figures, margins, internal notes) is permission-gated, not just hidden in the UI.

## 5. MVP Definition (what ships first)

**Must have (Phase 1 — Foundation):** Auth, multi-company, company profile, users, roles, permissions, subscription foundation, audit log.

**Must have (Phase 2 — Core Business):** Dashboard, Clients, Projects, Products/Categories/Subcategories, BOQ, Quotations, Invoices, Payments, Expenses, Reports.

**Explicitly deferred (not MVP):** Leads/CRM, Site Visits, Design Management, Contracts, Procurement, Site Management, Snags, Handover, Client Portal, Notifications, WhatsApp integration, subscription billing/usage limits/feature flags. See `09_Project/Roadmap.md` for phase sequencing (Phase 3–5).

## 6. Non-Goals (for now)

- Building every screen before the business workflow, role model, and lifecycles are approved (see `39_Requirement Approval Gate` in the source doc).
- Treating modules as independent CRUD screens instead of a connected workflow.
- A client-facing portal in the MVP.

## 7. Success Metrics (proposed — to validate with client)

- % of company's active projects with a complete BOQ → Quotation → Invoice chain (adoption of the core workflow vs. spreadsheets)
- Time from quotation sent to client approval
- Accuracy/timeliness of project profit/loss reporting vs. manual reconciliation
- Zero cross-tenant data access incidents

## 8. Open Questions for Client

1. Final confirmation of MVP module list (Phase 1–2) vs. desired Phase 3 pull-forward items.
2. Whether Client Portal should be pulled earlier than Phase 5.
3. Numbering/format conventions for quotations and invoices (per company or platform-standard).
4. Multi-currency requirement — single currency per company, or per-project?
5. Subscription/billing model details (plan tiers, usage limits) for Platform Admin.

See `09_Project/Roadmap.md` and `09_Project/Risk_Register.md` for delivery planning.
