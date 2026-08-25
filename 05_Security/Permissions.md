# Roles & Permissions (Draft)
## INT Projects — Multi-Company Interior & Architecture Management SaaS

**Status:** Draft — role responsibilities are well defined in the source requirements; exact permission-code granularity is proposed and needs client confirmation.

---

## 1. Model

```
User → Company Membership → Role → Permissions
```

- A `user` is a global identity (one login).
- A `company_membership` binds a user to one company with one role — this is where tenant scope and role actually live, not on the user record (see `05_Security/Tenant.md`, `03_Database/Database_Schema.md`).
- A `role` is a named bundle of `permission`s, scoped to a company (custom roles) or global defaults (Owner/Admin/PM/Designer/Accountant/Sales/Supervisor).

## 2. Permission Actions

Per the source requirements, permissions should support these action types per module:

`View · Create · Edit · Delete · Approve · Export · Manage · Financial access`

Proposed permission code format: `<module>.<action>` (e.g. `invoice.view`, `expense.approve`, `report.financial_access`).

## 3. Default Roles (from source requirements)

| Role | Representative Permissions |
|---|---|
| **Company Owner** | All modules, all actions, including company settings and subscription |
| **Company Admin** | Manage users/roles, manage clients/projects/products, view company reports |
| **Project Manager** | View/edit assigned projects, manage tasks, view project costs (not necessarily full financial module) |
| **Designer / Architect** | View assigned projects, manage designs/drawings/revisions, participate in approvals, manage project documents |
| **Accountant / Finance** | Full quotation/invoice/payment/expense access, financial reports, project profitability |
| **Sales / CRM User** | Leads, clients, follow-ups, site visits, quotations (create/view, not necessarily approve) |
| **Site Supervisor** (Phase 4) | Site visits, daily logs, labour/material tracking, snags |
| **Platform Super Admin** | Not a company role at all — operates on the separate platform surface (see `05_Security/Tenant.md` §6) |

Worked example from the source doc:

```
Accountant
├── View Invoice
├── Create Invoice
├── Edit Invoice
├── View Payment
├── Record Payment
├── View Expense
└── View Financial Reports
```

## 4. Custom Roles

Company Admins should be able to create custom roles by composing permission codes, not just use the fixed defaults above — the source requirements frame permissions as composable primitives ("View / Create / Edit / Delete / Approve / Export / Manage / Financial access" per module), which implies the platform should support role customization beyond the seven listed defaults, subject to client confirmation.

## 5. Enforcement Points

- **API layer:** every endpoint declares its required permission code(s); the Tenant/Permission middleware checks it after resolving company membership (see `05_Security/Tenant.md` §2) and before any business logic runs.
- **Frontend:** UI should hide/disable actions the current role can't perform, but this is a UX convenience only — see `05_Security/Tenant.md` §1, the API is the actual enforcement boundary.
- **Financial access** is called out explicitly in the source doc as its own permission dimension — meaning some roles (e.g. Designer, Site Supervisor) may see a project's operational data but not its financial figures (margins, costs) even within the same project.

## 6. Client Portal Permissions (Phase 5)

The client role is structurally different from internal roles: it is scoped not just by company but by a **single client record**, and must never see: other clients, other projects, internal expenses, employee salaries, internal notes, internal margins/profit, or other vendor information — unless explicitly permitted. This likely warrants a separate permission set/model rather than reusing the internal role/permission table, since the scoping unit (one client's own data only) is narrower than any internal role.

## 7. Open Items

1. Full canonical list of permission codes per module (to be enumerated alongside `04_API/` endpoint finalization).
2. Whether custom roles are MVP (Phase 1–2) or deferred.
3. Exact financial-access boundary for Project Manager (can they see project profit/loss, or only cost-to-date without margin)?
