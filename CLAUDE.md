# CLAUDE.md — INT Projects SaaS

This file gives Claude Code context on the product being built in this repository. It is derived from `INT_Projects_Client_Requirements_and_Business_Flow.md` (v1.0, 24 Aug 2026) — the client requirements & business flow document. Treat that document as the source of truth for requirements; this file is a working summary to orient any session in this repo.

## Product

A **multi-tenant SaaS platform** for interior design companies, interior contractors, architecture firms, turnkey project companies, furniture/interior execution businesses, and small/medium design studios. It replaces spreadsheets and disconnected tools with one system spanning: **Client acquisition → Project → BOQ → Quotation → Approval → Invoice → Payment → Expenses → Project profitability → Reports**.

Expanded future workflow: **Lead → Site Visit → Design → BOQ → Quotation → Contract → Procurement → Site Execution → Quality/Snagging → Handover → Warranty**.

Core framing: the client is not buying a CRM, invoice tool, expense tool, or product catalog individually — they are buying **one connected operating system**: Customer → Project → Commercial → Execution → Finance → Profitability.

## Status

This is currently a **requirements/discovery document**, not an approved spec. Per the source doc, do **not** start database design or full implementation until the "Requirement Approval Gate" (business flow, multi-company model, roles/permissions, project lifecycle, financial lifecycle, BOQ structure, quotation/invoice/payment/expense lifecycles, reporting definitions, client portal scope) is explicitly approved.

## Multi-Tenancy (fundamental, non-negotiable)

- The platform serves many independent **companies (tenants)**, each with its own Users, Clients, Projects, Products, Quotations, Invoices, Payments, Expenses, Reports.
- **Company A must never access Company B's data.** All company-owned records must be tenant-scoped.
- The **frontend must never be trusted** to supply a company ID for authorization — the server must derive tenant scope from authenticated identity + membership.
- Required request flow: Request → Authentication → Identify User → Identify Company → Check Membership → Check Permission → Tenant-Scoped Data Query → Business Logic → Response.

## User Roles

- **Platform Super Admin** — owns/operates the SaaS itself (companies, plans, subscriptions, platform settings, feature flags, audit); not a normal company user.
- **Company Owner** — full control of one company workspace.
- **Company Admin** — users, roles/permissions, clients, projects, products, reports.
- **Project Manager** — assigned projects, tasks, deadlines, team, cost tracking.
- **Designer / Architect** — designs/drawings, revisions, client approvals, documents.
- **Accountant / Finance** — quotations, invoices, payments, expenses, receivables, financial reports, project profitability.
- **Sales / CRM User** — leads, clients, follow-ups, site visits, quotations.
- **Site Supervisor** (future) — site visits, daily logs, photos, labour/material tracking, snags.
- **Client** (future portal, own login) — views/approves quotations & designs, views invoices/payment status, downloads documents, raises service/warranty requests. Must never see other clients, other projects, internal expenses, salaries, internal notes, or internal margins/profit.

Recommended model: `User → Company Membership → Role → Permissions` (view/create/edit/delete/approve/export/manage/financial-access), permissions assignable per role (e.g. Accountant gets invoice/payment/expense/financial-report permissions).

## Core Domain Model / Relationships

```
COMPANY
 └── USERS
 └── CLIENTS
      └── PROJECTS
           ├── BOQ → PRODUCTS
           ├── QUOTATIONS
           ├── CONTRACTS
           ├── INVOICES → PAYMENTS
           ├── EXPENSES
           ├── TASKS
           ├── DOCUMENTS
           └── SITE ACTIVITY
 └── REPORTS
```

Key entities and their bridges:
- **Project** — the central *operational* entity (Overview, Client, Team, Tasks, Milestones, Timeline, Design, Drawings, BOQ, Quotations, Contracts, Invoices, Payments, Expenses, Procurement, Site Activity, Documents, Snags, Reports).
- **Client** — the central *commercial* entity; reusable across multiple projects of the same company. Client 360 view: Basic Info, Contact Info, GST/Tax Info, Addresses, Contacts, Projects, Quotations, Contracts, Invoices, Payments, Documents, Notes, Activity.
- **Product / Work Item** — `Category → Subcategory → Product/Work Item → Unit → Default Cost → Default Selling Rate → Tax → Status`. Units: Nos, Sq.ft, Sq.m, Running ft, Kg, Litre, Set, Job.
- **BOQ** — bridges Project + Product/Work Item + Quantity + Rate: `Project → BOQ → Section → Item → Quantity → Unit → Rate → Amount` where `Amount = Quantity × Rate`. Supports discount, tax, notes, optional/alternative items.
- **Quotation** — bridges BOQ to commercial agreement. Flow: Project → BOQ → Create Quotation → Internal Review → Send to Client → Client Review → (Revision → new version) or (Approval). Fields: quote number, client, project, items, BOQ reference, subtotal, discount, tax, total, terms, payment schedule, validity, notes, attachments, versioning, approval status.
- **Contract** — Approved Quotation → Generate Contract → Terms/Scope/Payment Schedule → Client Acceptance → Contract Active.
- **Invoice** — Contract/Approved Quotation → Invoice → Send to Client → Payment. Statuses: Draft, Sent, Partially Paid, Paid, Overdue, Cancelled.
- **Payment** — linked to invoice, client, project (date, amount, method, reference, receipt, notes).
- **Expense** — Company, Project, Category, Vendor, Employee, Amount, Tax, Date, Payment Method, Receipt, Notes, Added By, Approval Status. Workflow: Draft → Submitted → Approved → Paid.
- **Project Costing**: `Revenue − Cost (Materials + Labour + Vendors + Procurement + Transport + Other) = Profit`, tracked with margin %.

## Project Status Lifecycle

`Draft → Planning → Design → Quotation → Approved → Execution → Quality Check → Handover → Completed`, plus `On Hold` / `Cancelled` side-states.

## Dashboard / Reports

KPIs: Total Projects, Active Projects, Total Quotations, Total Billed Revenue, Total Received, Pending Amount, Total Expenses, Net Profit/Loss — plus recent projects/quotations, pending payments, overdue invoices, recent expenses, upcoming deadlines, activity feed, project profitability.

Report groups: **Sales** (leads, quotations, approval/rejection, conversion rate), **Projects** (active/completed/delayed, progress, profitability), **Finance** (revenue, received, outstanding, expenses, P&L, receivables), **Expenses** (by category/project/vendor/employee/date).

## Future Expansion Modules (post-MVP)

- **Lead/CRM**: Lead → Qualification → Follow-up → Site Visit → Won → Client → Project. Lost leads need a loss reason and optional re-follow-up date.
- **Site Visit**: schedule, assign, capture info (measurements, requirements, photos, videos, budget, site conditions), produce a site visit report, create/update project.
- **Design Management**: versioned designs (Design V1/V2/V3, Approved V3 — not `final2.pdf`-style naming), internal review → client review → revision cycle → approval.
- **Procurement**: BOQ → Material Requirement → Purchase Request → Approval → Vendor → Purchase Order → Goods Receipt → Inventory → Material Issue → Site.
- **Site Management**: daily work logs (date, workers, work completed, materials used, issues, photos, progress %, next-day plan).
- **Snag Management**: Inspection → Create Snag → Assign → Fix → Verify → Close (location, description, priority, assignee, due date, photos, status, resolution).
- **Handover**: Execution Complete → All Tasks/Snags Closed → Final Inspection → Final Invoice → Final Payment → Handover Documents → Client Acceptance → Project Completed.
- **Client Portal**: separate login; dashboard with Progress, Designs, Approvals, Quotations, Invoices, Payments, Documents, Messages, Service Requests — strictly isolated per client.
- **Notifications**: in-app/email/(future WhatsApp) for assignments, overdue items, approvals, payments, deadlines.
- **Audit Trail**: who/what/old value/new value/when/entity for invoices, payments, expenses, quotations, permission changes, project changes — required for sensitive operations.

## MVP Phasing

1. **Foundation** — Auth, multi-company, company profile, users, roles, permissions, subscription foundation, audit log.
2. **Current Business Modules** — Dashboard, Clients, Projects, Products/Categories/Subcategories, BOQ, Quotations, Invoices, Payments, Expenses, Reports.
3. **Interior Workflow** — Leads, Site Visits, Design Management, Drawing/Revisions, Approvals, Tasks, Milestones, Documents.
4. **Execution** — Vendors, Procurement, Purchase Orders, Inventory, Site Management, Labour, Daily Logs, Snags, Handover.
5. **Advanced SaaS** — Client Portal, Employee Portal, Notifications, WhatsApp, Advanced Analytics, Subscription Billing, Usage Limits, Feature Flags.

## Target Architecture

```
Frontend
   ↓
API / Application Layer
   ↓
Business Modules
   ↓
Tenant / Permission Layer
   ↓
PostgreSQL
   ↓
Object/File Storage
```

Principles: multi-company from day one; strict tenant data isolation; role-based access control; Project as central operational entity, Client as central commercial entity; BOQ bridges products/work to quotation; Quotation bridges to commercial agreement; Invoice/Payment is the financial lifecycle; Expenses are project costs; Reports derive from transactional data (not separately maintained); versioning for quotations and designs; audit logs on sensitive operations; API-first, modular backend, permission-driven frontend, scalable file/document storage.

## Documentation Structure

The requirements above have been broken out into a full documentation tree — start there for detail beyond this summary:

- `00_Development_Standards/` — **highest priority, applies to all code in this repo**: Folder Structure, Naming Conventions, Git Strategy, Branch Naming, Commit Message Format, Code Review Checklist, Logging Standards, Error Handling, Validation Standards, API Response Format. Every future session writing or reviewing code in this repo should read this folder first — it is not optional guidance, it's the binding standard.
- `01_Business/` — BRS, FRS, PRD (drafted)
- `02_Architecture/` — Solution Architecture, Technical Architecture (stack confirmed: React/TS/Vite/Tailwind/shadcn + Django/DRF + PostgreSQL), HLD (drafted); LLD (blocked on schema/API finalization)
- `03_Database/` — ER Diagram, Database Schema, Naming Standards, **Migration Plan** (001–027, dependency-ordered) (all drafted, MVP scope)
- `04_API/` — Authentication, CRM, Project, BOQ, Finance API sketches (drafted)
- `05_Security/` — JWT, Tenant isolation, Permissions (drafted — read `Tenant.md` before touching any data-access code)
- `06_UI/` — full design system (drafted): `Design_Principles`, `Design_Tokens` (color/type/spacing/radius/shadow/motion), `Component_Inventory`, `Application_Shell_Navigation`, `Responsive_Accessibility`, `Wireframes` (screen briefs + module build sequence), `UI_Guidelines` (index). Read `UI_Guidelines.md` first before designing or building any screen.
- `07_DevOps/` — fully drafted: Development Environment, Staging, Production, Docker, CI/CD, Backup Strategy, Monitoring, Logging (infra), Rollback Process. Only the cloud provider/region and a few hosting specifics remain open (`Production.md` §6) — the operational model itself is defined.
- `08_QA/` — `Test_Strategy.md` (index/pyramid) + Unit, Integration, API, E2E, Performance, Security Tests, UAT (with sign-off checklist), Test Cases (drafted)
- `09_Project/` — Roadmap, Risk Register, **Module Dependency Map** (binding build order: Auth→Company→User→Role→Client→Project→Product→BOQ→Quotation→Invoice→Payment→Expense→Reports) (drafted); Sprint Planning (stub)

Everything is marked **Draft** and pending the client's Requirement Approval Gate (see `01_Business/BRS.md` §9) — do not treat any schema, API, or architecture doc here as final enough to build against without checking its own "Open Items"/"Open Decisions" section first.

## Working Notes for Claude Code Sessions

- The existing (legacy) system already has working Users, Clients, Projects, Products/Categories/Subcategories, Quotations, Expenses, Reports, and Dashboard screens — but they behave as **independent CRUD screens**. The architectural task is to connect them into the single workflow above, not rebuild them from scratch.
- When implementing any company-owned entity (Client, Project, Product, Quotation, Invoice, Payment, Expense, Report, etc.), always scope queries and mutations by company/tenant ID resolved server-side from the authenticated session — never from a client-supplied field.
- Do not build out Phase 3–5 features (Leads, Site Visits, Design mgmt, Procurement, Site mgmt, Snags, Handover, Client Portal, Notifications) until Phases 1–2 are solid, unless the user explicitly asks to jump ahead.
- Full source document: `INT_Projects_Client_Requirements_and_Business_Flow.md` in this repo. Update this CLAUDE.md if that document is revised or superseded.


# Engineering Execution Rules

Before writing code:

1. Review architecture.

2. Review dependencies.

3. Review current sprint.

4. Review current task.

5. Explain implementation plan.

6. Implement only current task.

7. Write tests.

8. Update Swagger.

9. Update documentation.

10. Wait for review.

Never implement future modules unless instructed.

Never skip architecture.

Always follow Development Standards.

Always follow Module Dependency Map.

Always follow Tenant Rules.

Always follow RBAC.