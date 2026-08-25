# Business Requirements Specification (BRS)
## INT Projects — Multi-Company Interior & Architecture Management SaaS

**Status:** Draft (derived from client requirements discovery) — pending approval
**Source:** `INT_Projects_Client_Requirements_and_Business_Flow.md`

---

## 1. Business Problem

Interior design companies, contractors, architecture firms, turnkey project companies, and furniture/interior execution businesses currently run their operations across disconnected spreadsheets, documents, and manual calculations. There is no single system that connects client acquisition, project delivery, commercial documents (BOQ/quotation/invoice), and financial outcomes (payments/expenses/profitability).

## 2. Business Objective

Replace disconnected tools with **one centralized, multi-tenant platform** that lets a company manage its full business lifecycle:

`Client acquisition → Project creation → BOQ → Quotation → Approval → Invoice → Payment → Expenses → Project profitability → Reports`

and, in later phases, the full interior-business lifecycle:

`Lead → Site Visit → Design → BOQ → Quotation → Contract → Procurement → Site Execution → Quality/Snagging → Handover → Warranty`

## 3. Business Questions the System Must Answer

- How many projects are active, and which clients own which projects?
- What quotation was sent, and has it been approved?
- How much has been invoiced, received, and is still outstanding?
- What has each project cost (labour, materials, other), and what is its profit/loss?
- Who is responsible for each project?
- What products/materials are available and at what rate?
- What work is pending, and what financial reports exist?

## 4. Stakeholders / Target Users

| Role | Core Responsibility |
|---|---|
| Platform Super Admin | Owns/operates the SaaS: companies, plans, subscriptions, platform settings, audit |
| Company Owner | Owns one company workspace end-to-end |
| Company Admin | Users, roles/permissions, clients, projects, products, company reports |
| Project Manager | Assigned projects, tasks, deadlines, team coordination, cost tracking |
| Designer / Architect | Designs, drawings, revisions, client approvals, project documents |
| Accountant / Finance | Quotations, invoices, payments, expenses, receivables, financial reports |
| Sales / CRM User | Leads, clients, follow-ups, site visits, quotations |
| Site Supervisor (future) | Site visits, daily logs, labour/material tracking, snags |
| Client (future portal) | Views/approves quotations & designs, views invoices/payments, raises service requests |

Platform Super Admin is **not** a company user — it operates above the tenant layer.

## 5. Fundamental Business Rule: Multi-Company Isolation

The platform must serve many independent companies (tenants) on one codebase. **A company must never be able to access another company's business data** — this is a hard business requirement, not just a technical nice-to-have, because it directly affects client trust and contract terms.

## 6. Business Value / What the Client Is Buying

The client is not buying a CRM, an invoice tool, an expense tool, or a product catalog in isolation. They are buying a **single operating system for an interior/architecture business** that connects:

`Customer → Project → Commercial → Execution → Finance → Profitability`

## 7. Scope Boundaries (Business Level)

**In scope for MVP (Phase 1–2):** authentication, multi-company foundation, users/roles/permissions, dashboard, clients, projects, products, BOQ, quotations, invoices, payments, expenses, reports.

**Deferred to later phases (Phase 3–5):** leads/CRM, site visits, design management, procurement, site/labour management, snags, handover, client portal, notifications, subscription billing, feature flags. See `09_Project/Roadmap.md`.

## 8. Success Criteria

- A company can be onboarded and operate without any visibility into another company's data.
- A project's full commercial and financial lifecycle (BOQ → Quotation → Invoice → Payment → Expense → Profit/Loss) can be tracked in one place, replacing spreadsheets.
- Reports reflect real transactional data, not manually reconciled numbers.

## 9. Open Items Requiring Client Sign-off

See `39_Requirement Approval Gate` in the source requirements document — business flow, multi-company model, role/permission model, project/financial/BOQ/quotation/invoice/expense lifecycles, reporting definitions, and client portal scope must be confirmed before database/API design begins.
