# Application Shell & Navigation Architecture

**Status:** Draft — Steps 10–11 of the design system build sequence.

---

## 1. Shell Layout (Desktop)

```
┌───────────────────────────────────────────────────────────────┐
│  Top Header  (breadcrumb/title · search · quick-create ·        │
│               notifications · help · theme toggle · user menu)  │
├───────────────┬─────────────────────────────────────────────────┤
│               │                                                 │
│   Sidebar     │            Main Content                        │
│  (quiet       │                                                 │
│   chrome)     │                                                 │
│               │                                                 │
└───────────────┴─────────────────────────────────────────────────┘
```

The shell itself uses `bg-surface-secondary` (sidebar) against `bg-app` (main content), with `border-subtle` as the only separator — no drop shadow between sidebar and content. "Quiet chrome": the sidebar must never visually compete with the content it's navigating to (`Design_Principles.md` §2).

## 2. Sidebar

**Expanded mode:** full labels + icons, ~240px wide.
**Collapsed mode:** icons only, ~64px wide, labels appear in a tooltip on hover.
Transition between modes: width + label opacity animate together at `motion-slow` (`Design_Tokens.md` §6) — never an instant snap.

**Contents, top to bottom:**
1. Brand mark (compact logo, links to Dashboard)
2. Workspace/company switcher (§4)
3. Primary navigation (§3)
4. Favorites/recent (user-pinned or recently visited records — clients, projects)
5. Secondary navigation (Settings, Help)
6. User profile menu (§7, `Component_Inventory.md`-driven dropdown)

**Active item indicator:** a slim (2–3px) `accent-500` bar on the left edge of the active nav item, animating its vertical position with `motion-standard` when navigation changes — not a filled background block, which reads as heavier than this system's restraint calls for.

## 3. Primary Navigation — Information Architecture

Grouped by business domain, matching the module map in `01_Business/FRS.md`:

```
Overview
  └─ Dashboard

CRM
  ├─ Leads            (Phase 3)
  ├─ Clients
  ├─ Contacts
  ├─ Follow-ups        (Phase 3)
  └─ Activities

Projects
  ├─ Projects
  ├─ Tasks
  ├─ Calendar
  ├─ Team
  └─ Documents

Sales
  ├─ Quotations
  ├─ Products
  └─ Services

Finance
  ├─ Invoices
  ├─ Payments
  └─ Expenses

Analytics
  ├─ Reports
  └─ Analytics

Communication            (Phase 5)
  ├─ WhatsApp
  ├─ Email
  └─ Notifications

Administration
  ├─ Employees
  ├─ Roles & Permissions
  ├─ Organization
  └─ Settings
```

**MVP note:** only render the groups/items that correspond to Phase 1–2 modules (`09_Project/Roadmap.md`) — Leads, Follow-ups, and Communication are shown here for the complete target IA but must not appear in the nav until their phase ships (an empty/disabled nav entry for an unbuilt feature is worse than no entry at all).

Sections collapse/expand independently (nested disclosure), remembering the user's last state per session. Only one top-level section needs to be expanded at a time by default, matching the user's current location.

## 4. Workspace/Company Switcher

Positioned directly under the brand mark. Shows the current company name + a small chevron; opens a dropdown listing every company the authenticated user has an active `company_membership` in (`05_Security/Tenant.md`), plus a "+ Create workspace" action (visible only to users with platform-level company-creation rights, or omitted entirely for a standard company user, per role).

```
INT Projects

Workspace A   ✓
Workspace B
Workspace C

+ Create workspace
```

Switching companies triggers a full context reload (new tenant scope resolved server-side per the request flow in `05_Security/Tenant.md` §2) — never a client-side-only swap of a `companyId` variable.

## 5. Command Palette

Trigger: `Ctrl+K` / `Cmd+K`, opens as a centered overlay (`Component_Inventory.md` §5 Dialog treatment, `motion-slow` scale+fade).

```
Search anything...

Clients        (matches by name/company)
Projects       (matches by name)
Invoices       (matches by invoice number)
Quotations     (matches by quote number)

Create:
+ Client
+ Project
+ Quotation
+ Invoice

Actions:
Export data
Open settings
Switch workspace
```

- Search results are scoped to the current company (tenant-scoped, same as every other query — `05_Security/Tenant.md`) and to what the current role is permitted to see.
- Fully keyboard-navigable: arrow keys move selection, `Enter` confirms, `Esc` closes.
- Search endpoints are the same `04_API/` module APIs the rest of the app uses (Clients, Projects, Invoices, Quotations) with a lightweight `?q=` search param — not a separate parallel search index for MVP.

## 6. Top Header

**Left:** breadcrumb trail (reflects the current nesting, e.g. `Projects / Riverside Villa / BOQ`) + page title.

**Right, in order:** global search trigger (opens Command Palette), Quick Create (§8), Notifications bell (opens `Component_Inventory.md` §16 Notification Drawer, unread count as a subtle dot), Help, theme toggle (light/dark, respects but can override OS preference), user menu (§7).

## 7. User Profile Menu

```
Profile
Preferences
Notifications
Security
Appearance
Organization
Billing
─────────
Logout
```

Items shown are filtered by what the current role/company setup makes relevant (e.g. "Billing" only for Company Owner, "Organization" only for Owner/Admin) — same principle as §9 role-based nav.

## 8. Quick Create

A single "+" affordance in the header opening a compact command-menu-style list, not a giant modal with every field:

```
+ New Client
+ New Lead        (Phase 3)
+ New Project
+ New Quotation
+ New Invoice
+ New Expense
+ New Task
```

Selecting an item opens that entity's create form (Dialog or Drawer per `Component_Inventory.md` §5, depending on form length) rather than navigating away from the current page — quick create must not lose the user's place.

## 9. Role-Based Navigation

Per `05_Security/Permissions.md`, the sidebar and header render only the sections/actions the current role has `.view` permission for — an inaccessible module is **absent from the nav**, not present-but-disabled-with-a-lock-icon. This is a deliberate product decision (`01_Business/FRS.md` §5 role table): a Designer never sees "Payments" as a grayed-out temptation; it simply isn't in their sidebar. The backend permission check remains the actual authority (`05_Security/Permissions.md` §5) — hiding nav items is a UX courtesy, never the security boundary itself.

| Role | Sidebar Scope (representative) |
|---|---|
| Owner | Everything |
| Admin | Everything except platform/billing internals reserved for Owner |
| Project Manager | Projects, Tasks, Calendar, Team, Clients (view), Reports (project-scoped) |
| Designer/Architect | Projects (assigned), Documents, limited Finance visibility |
| Accountant | Finance (full), Sales (Quotations/Invoices), Reports (financial), Clients (view) |
| Sales/CRM | CRM (full), Sales (Quotations), Clients, limited Project visibility |

## 10. Platform Admin Console — Separate Shell

Per `00_Development_Standards/Folder_Structure.md` §1, the Platform Super Admin console is a **separate app**, not a route inside this shell — it has its own header/nav scoped to Companies/Plans/Subscriptions/Usage/Feature Flags/Platform Users/Support/Audit Logs (`01_Business/FRS.md` §1), reinforcing the architectural separation from company-tenant context established in `05_Security/JWT.md` §6.
