# Screen Inventory & Build Sequence

**Status:** Draft. This document replaces the earlier placeholder — it is the screen-by-screen brief for design work, not yet pixel-level wireframes. Actual wireframe artboards (via the `design` skill) are produced one module at a time, in the sequence below, each approved before the next starts — per `Design_Principles.md` §6's quality bar and the source master prompt's explicit instruction not to build every screen at once.

---

## Build Sequence

Design work proceeds in this exact order. Do not start a step before the prior one is approved.

1. **Design System** — `Design_Principles.md`, `Design_Tokens.md`, `Component_Inventory.md` (done — this doc set)
2. **Application Shell** — `Application_Shell_Navigation.md` (done — this doc set)
3. **Dashboard**
4. **Clients** (list)
5. **Client Detail**
6. **Projects** (list)
7. **Project Detail**
8. **Quotations**
9. **Invoices**
10. **Expenses**
11. **Products**
12. **Reports**
13. **Employees / Roles & Permissions**
14. **Settings**
15. **Responsive + Accessibility pass** across everything above

Steps 3–14 map directly onto the module build order in `09_Project/Module_Dependency_Map.md` — design work for a module should track close behind (not far ahead of, and not after) that module's backend/API implementation, so screens are designed against real data shapes (`04_API/`) rather than speculative ones.

---

## Screen Briefs

Each brief below is the *content and hierarchy brief* for that screen — the actual visual layout is produced as wireframe artboards when that step in the sequence is reached, using only components from `Component_Inventory.md`.

### Dashboard
Answers: *"What requires my attention right now?"* — not a wall of every available metric.
- **Welcome area:** contextual greeting + date, sets a personal, not corporate-generic, tone
- **KPI strip:** Revenue, Outstanding Invoices, Active Projects, New Leads (Phase 3), Conversion Rate (Phase 3), Expenses — compact `Stat`/KPI Cards (`Component_Inventory.md` §4), each with value + comparison + trend + optional sparkline. Only MVP-relevant KPIs render in Phase 1–2 (`01_Business/FRS.md` §6); Lead/Conversion cards appear once Phase 3 ships.
- **Attention Center:** actionable list of what's overdue/pending/at-risk (overdue invoices, quotations awaiting approval, deadlines approaching) — each item includes the record's key figure and a direct action (`[View Invoice]`, `[Send Reminder]`), not just a link to a list.
- **Activity Timeline:** recent business events (`Component_Inventory.md` §14), reverse-chronological.
- **Layout hierarchy (top to bottom):** Welcome → Primary KPIs → Attention Required → Recent Activity. The most important number appears first; not every available metric is shown just because it exists.

### Clients (List)
- `DataTable` (`Component_Inventory.md` §3) as the primary interface — not a card grid.
- Columns: Client, Company, Email, Phone, Projects, Revenue, Outstanding, Status, Last Activity, Actions.
- Search, filters, saved views, sort, column visibility, pagination, bulk actions, export, "+ Add Client."

### Client Detail
A workspace, not a CRUD form.
- Header: name, company, status, primary actions (`[Edit]` `[Create Quotation]` `[Create Invoice]` `[More]`).
- Tabs: Overview, Projects, Quotations, Invoices, Payments, Activities, Documents, Notes (matches Client 360 in `01_Business/FRS.md` §7).
- Overview tab composes: client summary, financial summary (billed/received/outstanding), active projects, recent activity, contact info.

### Projects (List)
- Grid/List toggle. Grid uses Project Cards (`Component_Inventory.md` §4): name, client, progress, deadline, budget, team avatars (`Component_Inventory.md` §8), status badge.
- Filters: status, client, manager, deadline, progress, budget.

### Project Detail
The strongest workspace in the product — Project is the central operational entity (`02_Architecture/Solution_Architecture.md` §3).
- Header: name, client, status, progress, actions (`[Edit]` `[Add Task]` `[Create Quote]` `[More]`).
- Tabs: Overview, Tasks (Kanban — `Component_Inventory.md` §15), Timeline, Team, Budget, Quotations, Invoices, Files, Activity.
- Overview composes: progress, deadline, budget vs. actual cost (`01_Business/FRS.md` §18), team, milestones, recent activity.

### Quotations (Builder + List)
- Builder: client/items/services/quantity/rate/discount/tax on the left/center; a **live-updating** summary panel on the right (subtotal/discount/tax/grand total) that recomputes smoothly as line items change (client-side preview only — the server recomputes authoritatively per `00_Development_Standards/Validation_Standards.md` §3).
- Actions: Save Draft, Preview, Download PDF, Send, Duplicate, Approve, Reject — mapped to `04_API/Finance_API.md` quotation endpoints.
- List: standard `DataTable`, status column using semantic Badge colors only (`Component_Inventory.md` §7).

### Invoices
- Fields: invoice number, client, issue date, due date, items, taxes, discounts, payment status, notes.
- Status Badge values: Draft, Sent, Viewed, Partially Paid, Paid, Overdue, Cancelled — semantic color per status, computed server-side (`00_Development_Standards/API_Response_Format.md` §3), never client-set.

### Expenses
- Summary strip: Total Expenses, Monthly Expenses, Category Breakdown (donut, `Component_Inventory.md` §13, used here because it's a genuine part-to-whole case).
- Table: Date, Description, Category, Project, Amount, Employee, Receipt, Status.
- Receipt upload with inline preview (`Component_Inventory.md` §2 FileUpload).

### Products & Services
- List: SKU, category, price, tax, status, search, filters.
- Must support quick-select from within the Quotation/BOQ builder (reused component, not a separate picker implementation).

### Reports
Not a wall of charts — each section answers one business question (`Design_Principles.md` §2):
- Revenue, Projects, Clients, Quotations, Invoices, Expenses, Employee performance (Phase 3+), Lead conversion (Phase 3).
- Mix of line/bar charts, tables, and KPI comparisons per section — donut only where genuinely part-to-whole. Charts animate in once on viewport entry (`motion-emphasis`), not on every re-render.

### Employees / Roles & Permissions
- User list + invite flow (`04_API/Authentication_API.md` §User Invitation).
- Role/permission matrix editor reflecting `05_Security/Permissions.md` §2's action grid (View/Create/Edit/Delete/Approve/Export/Manage/Financial access) per module.

### Settings
- Company profile, branding, tax settings, invoice/quotation numbering, currency, payment terms, notification settings (`01_Business/FRS.md` §2).

---

## Forward-Looking Surfaces (documented now, not built until their phase)

Two categories of screen are referenced in the original design brief but belong to later roadmap phases (`09_Project/Roadmap.md`) — noted here so the design system already has a home for them when the time comes, without building them prematurely (`Design_Principles.md` §1's explicit sequencing rule):

- **AI-native surfaces** (Phase 5): insight cards, inline suggestions, contextual assistant panels — e.g. a client AI summary, "projects at risk" detection, invoice-likely-to-be-overdue flags. These render using the AI Surface Accent token (`Design_Tokens.md` §1.7) and live *inside* existing workflows (a card on Client Detail, a badge on the Project list) — never as a floating generic chatbot bubble.
- **Communication module** (Phase 5): WhatsApp/Email integration screens, dependent on the notification transport decision in `02_Architecture/Technical_Architecture.md` §8 item 6.

## Related

- `06_UI/UI_Guidelines.md` — index and cross-cutting guardrails for all of the above
- `08_QA/Test_Cases.md` / `08_QA/UAT.md` — what "done" means functionally for each of these screens
