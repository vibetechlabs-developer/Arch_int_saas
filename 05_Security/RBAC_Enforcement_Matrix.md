# RBAC Enforcement Matrix — BE-054 Preparation & Implementation

**Status:** Implemented, pending Backend Lead review (`BE-054` = **Review** in `BACKEND_TASKS.md`, not Done — the Backend Lead has not self-approved this). §§1–6 below are the original pre-implementation planning matrix (kept verbatim for traceability). §7 onward documents what was actually built, the approved decisions it encodes, and the migration-safety findings raised during validation.

**Scope:** Every business endpoint across `companies`, `roles` (+ `permissions`, `company-memberships`), `clients`, `projects` (+ team), `products` (+ categories/subcategories), `boq` (+ sections/items), `quotations`, `invoices`, `payments`, `expenses`, `documents`, `reports`, `dashboard`, `audit`. Authentication-surface endpoints (`/auth/login`, `/auth/me`, `/auth/refresh`, `/auth/memberships`, password reset) are identity endpoints, not company-owned business resources, and are out of scope.

**Method:** Direct inspection of `urls.py`/`views.py`/`permissions.py` for every listed app (companies/roles inspected directly; clients/projects/products/boq, quotations/invoices/payments/expenses, and documents/reports/dashboard/audit inspected via three parallel research passes), cross-referenced against `apps/users/permission_catalog.py` (BE-049's seeded catalog) and `05_Security/Permissions.md`.

---

## 1. What's true for every single row below (stated once, not repeated 70 times)

- **Platform Admin behavior:** identical everywhere — `is_platform_admin(request)` short-circuits both `has_permission` and `has_object_permission` to `True`, unconditionally, on every endpoint in this codebase with no exception. Any RBAC cutover must decide explicitly whether Platform Admin keeps this universal bypass for *business* data (recommended: yes, for support/ops purposes) or is narrowed — see §5.
- **Current tenant behavior:** identical everywhere — `has_permission` requires `request.user.is_authenticated` and a resolved `request.company_id`; `has_object_permission` requires `str(request.company_id) == str(obj.company_id)`. This is **tenant isolation only** — every permission class in the codebase (`ClientPermission`, `ProjectPermission`, `ProductCategoryPermission`, `RolePermission`, `CompanyMembershipPermission`, `IsPlatformAdminOrCompanyAccess`) implements this exact logic, and `apps/documents`, `apps/reports`, `apps/dashboard`, `apps/audit` don't even define their own permission class — they import and reuse `apps.projects.permissions.ProjectPermission` directly. **Zero role- or permission-code differentiation exists anywhere today.** Any authenticated member of a tenant can currently do anything within that tenant, including every workflow/approval action (quotation approve/reject, invoice cancel, payment void, expense approve/mark-paid).
- **Migration/compatibility risk — general:** the risk is the same shape for nearly every row: **today, every existing seeded user and every membership with no role assigned can do everything within their tenant.** The moment any endpoint starts checking a permission code, a membership with `role=None` (which is every membership that existed before BE-050, and every membership created without explicitly assigning a role) has **zero** codes (`PermissionService` fails closed) and loses access to that endpoint entirely. This is the single largest compatibility risk for the whole cutover, not any individual endpoint — see §6.

---

## 2. Category A — Explicitly documented, safe to enforce now

`05_Security/Permissions.md` §3's worked example is the **only** place the source requirements literally name concrete `<module>.<action>` pairs (as opposed to the format and action vocabulary in the abstract):

> Accountant → View Invoice, Create Invoice, Edit Invoice, View Payment, Record Payment, View Expense, View Financial Reports

| # | Method | Endpoint | Proposed code | Financial? |
|---|---|---|---|---|
| A1 | GET | `/invoices/{id}`, `/projects/{id}/invoices` | `invoice.view` | Yes |
| A2 | POST | `/projects/{id}/invoices` | `invoice.create` | Yes |
| A3 | PATCH | `/invoices/{id}` | `invoice.edit` | Yes |
| A4 | GET | `/invoices/{id}/payments` | `payment.view` | Yes |
| A5 | POST | `/invoices/{id}/payments` | `payment.create` | Yes |
| A6 | GET | `/expenses/{id}`, `/projects/{id}/expenses` | `expense.view` | Yes |
| A7 | GET | `/reports/finance`, `/reports/expenses` | `report.financial_access` | Yes |

**That is the entire explicitly-documented list — 7 codes, all financial.** Everything else below — all 34 remaining seeded codes, and every workflow/approval action found during this audit — is a Backend-Lead inference from the documented format (`<module>.<action>`) and action vocabulary (view/create/edit/delete/approve/export/manage/financial_access), not a client-approved concrete list. `Permissions.md` §7 item 1 ("full canonical list… pending client sign-off") remains open. Per your instruction, none of Category B should be silently enforced.

---

## 3. Category B — Inferred, requires approval before enforcement

Organized by module. "Code" is the BE-049-seeded catalog code being proposed for that action unless marked **NEW** (a code this audit surfaced a need for that is *not yet* in the catalog — see §4 for the full list and recommended defaults). "Risk" flags anything beyond the general risk in §1.

### Company (`apps/company`)

| Method | Endpoint | Current check | Proposed code | Doc'd? | Financial? | Risk |
|---|---|---|---|---|---|---|
| GET | `/companies` | Platform Admin only (non-admins get 403 at `has_permission`) | — (Platform-Admin-exclusive; not governed by any company-level RBAC code) | N/A | No | None — already stricter than tenant-only |
| POST | `/companies` | Platform Admin only | — (Platform-Admin-exclusive) | N/A | No | None |
| GET | `/companies/{id}` | Platform Admin OR object company-match | `company.view` | Inferred | No | Low |
| PATCH/PUT | `/companies/{id}` | Platform Admin OR object company-match | `company.manage` | Inferred | No | Low |
| DELETE | `/companies/{id}` | Platform Admin only | — (Platform-Admin-exclusive) | N/A | No | None |

### Roles, Permissions, Company Membership (`apps/users`) — BE-014/049/052

| Method | Endpoint | Current check | Proposed code | Doc'd? | Financial? | Risk |
|---|---|---|---|---|---|---|
| GET | `/roles`, `/roles/{id}` | Tenant-only | `role.view` | Inferred | No | Low |
| POST | `/roles` | Tenant-only | `role.manage` | Inferred | No | Medium — a company with no member holding `role.manage` could lock itself out of ever creating a role; Owner always gets it (seeded `__all__`), so only a risk if Owner's own membership has no role assigned |
| PATCH/PUT/DELETE | `/roles/{id}` | Tenant-only | `role.manage` | Inferred | No | Same as above |
| PUT | `/roles/{id}/permissions` | Tenant-only | `role.manage` | Inferred | No | Same as above — this is itself an RBAC-configuration action |
| GET | `/permissions` | `IsAuthenticated` only, no tenant check at all (intentional — global reference catalog) | none (leave open to any authenticated user) | N/A | No | None — read-only, non-sensitive reference data |
| GET | `/company-memberships`, `/{id}` | Tenant-only | `user.view` | Inferred | No | Low |
| POST | `/company-memberships` (invite) | Tenant-only | `user.manage` | Inferred | No | Same lockout shape as `role.manage` |
| DELETE `/{id}`, POST `/{id}/assign-role`, `/{id}/suspend`, `/{id}/reactivate` | Tenant-only | `user.manage` | Inferred | No | Same as above |

### Clients (`apps/clients`)

| Method | Endpoint | Current check | Proposed code | Doc'd? | Financial? | Risk |
|---|---|---|---|---|---|---|
| GET | `/clients`, `/clients/{id}` | Tenant-only | `client.view` | Inferred | No | Low |
| POST | `/clients` | Tenant-only | `client.create` | Inferred | No | Low |
| PATCH/PUT | `/clients/{id}` | Tenant-only | `client.edit` | Inferred | No | Low |
| DELETE | `/clients/{id}` | Tenant-only | `client.delete` | Inferred | No | Low |

### Projects (`apps/projects`)

| Method | Endpoint | Current check | Proposed code | Doc'd? | Financial? | Risk |
|---|---|---|---|---|---|---|
| GET | `/projects`, `/projects/{id}` | Tenant-only | `project.view` | Inferred | No | Low |
| POST | `/projects` | Tenant-only | `project.create` | Inferred | No | Low |
| PATCH/PUT | `/projects/{id}` | Tenant-only | `project.edit` | Inferred | No | Low |
| DELETE | `/projects/{id}` | Tenant-only | `project.delete` | Inferred | No | Low |
| **PATCH** | **`/projects/{id}/status`** | Tenant-only, **no distinct code today** | `project.edit` (default) or **NEW** `project.status_manage` | Inferred | No | **Medium** — a real workflow action (draft→…→completed, on_hold, cancelled) governed by an internal transition graph; today indistinguishable from a plain field edit. Designer/PM roles seeded in BE-049 both get `project.edit`, so either mapping is currently equivalent in practice — but if a future role should be able to edit project text fields without controlling lifecycle status, these need to split. Flagged, not decided. |
| GET | `/projects/{id}/team` | Tenant-only (via parent Project) | `project.view` | Inferred | No | Low |
| POST | `/projects/{id}/team` | Tenant-only | `project.manage` | Inferred | No | Low |
| DELETE | `/projects/{id}/team/{userId}` | Tenant-only | `project.manage` | Inferred | No | Low |

### Products, Categories, Subcategories (`apps/products`)

| Method | Endpoint | Current check | Proposed code | Doc'd? | Financial? | Risk |
|---|---|---|---|---|---|---|
| GET | `/product-categories`(`/{id}`), `/product-subcategories/{id}`, nested subcategory list | Tenant-only | `product.view` | Inferred | No | Low |
| POST/PATCH/PUT/DELETE | same category/subcategory endpoints | Tenant-only | `product.manage` | Inferred | No | Low |
| GET | `/products`, `/products/{id}` | Tenant-only | `product.view` | Inferred | **Yes** — `defaultCost`, `defaultSellingRate`, `taxRate` returned on every read | **Medium** — no seeded role currently gets `product.view` *without* also getting cost/rate visibility; there is no separate "see the catalog but not its cost basis" code in the catalog. Flagged as a real gap if that distinction ever matters (e.g. a Sales user who should see selling rate but not internal cost). |
| POST/PATCH/PUT/DELETE | `/products`(`/{id}`) | Tenant-only | `product.manage` | Inferred | Yes (cost/rate/tax accepted as input) | Same as above |

### BOQ (`apps/boq`) — reuses `ProjectPermission` directly, no BOQ-specific class

| Method | Endpoint | Current check | Proposed code | Doc'd? | Financial? | Risk |
|---|---|---|---|---|---|---|
| GET | `/projects/{id}/boq`, `/boq/summary` | Tenant-only (via parent Project) | `boq.view` | Inferred | **Yes** — item rate/discount/tax/amount; summary returns subtotal/discount/tax/total | Medium — same "view vs. see the money" gap as Products; no separate BOQ financial code exists. Designer role (BE-049) gets `boq.view`, which under this mapping means Designer sees full line-item rates — matches Permissions.md's loose framing ("Designer… may see a project's operational data but not its financial figures… even within the same project") only if BOQ rates aren't considered "financial figures" in that sense. **This is a genuine open question, not a mechanical mapping** — flagged for Backend Lead decision. |
| POST | `/projects/{id}/boq/sections`, `/sections/{id}/items` | Tenant-only | `boq.create` | Inferred | Yes (rate/discount/tax on item creation) | Same as above |
| PATCH/PUT | `/boq-sections/{id}`, `/boq-items/{id}` | Tenant-only (object check against parent `.boq`, not the section/item itself) | `boq.edit` | Inferred | Yes | Same as above |
| DELETE | `/boq-sections/{id}`, `/boq-items/{id}` | Tenant-only | `boq.delete` | Inferred | No | Low |

### Quotations (`apps/quotations`)

| Method | Endpoint | Current check | Proposed code | Doc'd? | Financial? | Risk |
|---|---|---|---|---|---|---|
| GET | `/projects/{id}/quotations`, `/quotations/{id}` | Tenant-only | `quotation.view` | Inferred | Yes | Low |
| POST | `/projects/{id}/quotations` | Tenant-only | `quotation.create` | Inferred | Yes | Low |
| POST | `/quotations/{id}/revise` | Tenant-only, **no distinct code today** | `quotation.edit` (default) or **NEW** `quotation.revise` | Inferred | Yes | Medium — creates a new version rather than mutating; conceptually closer to "create" than "edit." Recommending default = reuse `quotation.edit` to avoid catalog growth unless the Backend Lead wants create/revise/edit split three ways. |
| POST | `/quotations/{id}/send` | Tenant-only, **no code today** | `quotation.edit` (default) or **NEW** `quotation.send` | Inferred | Yes | Medium — merges "can edit a draft" with "can commit the company to a client-facing send." A Designer with `quotation.view` only (no edit) can't send today either way, so low practical difference at seed-role level, but worth a explicit decision since sending is externally visible. |
| POST | `/quotations/{id}/approve` | Tenant-only | `quotation.approve` | Inferred | Yes | Low — already has a dedicated code in the catalog |
| POST | `/quotations/{id}/reject` | Tenant-only, **no distinct code today** | `quotation.approve` (default — same reviewer authority as approve) or **NEW** `quotation.reject` | Inferred | Yes | Low-Medium — recommend reusing `quotation.approve` since approve/reject are two outcomes of the same review action, not separately delegable in the docs |
| — | (no DELETE endpoint exists) | — | `quotation.delete` (seeded, currently unused — no endpoint to attach it to) | Inferred | — | None — flag as dead code in the catalog until/unless a delete endpoint is added |

### Invoices (`apps/invoices`)

| Method | Endpoint | Current check | Proposed code | Doc'd? | Financial? | Risk |
|---|---|---|---|---|---|---|
| GET | `/projects/{id}/invoices`, `/invoices/{id}` | Tenant-only | `invoice.view` | **Documented** (§2 above) | Yes | Low |
| POST | `/projects/{id}/invoices` | Tenant-only | `invoice.create` | **Documented** | Yes | Low |
| PATCH | `/invoices/{id}` | Tenant-only (draft-only guard is a service-layer 409, not a permission check) | `invoice.edit` | **Documented** | Yes | Low |
| POST | `/invoices/{id}/send` | Tenant-only, **no code today** | `invoice.edit` (default) or **NEW** `invoice.send` | Inferred | Yes | Medium — same send-vs-edit question as quotations |
| POST | `/invoices/{id}/cancel` | Tenant-only, **no code today** | `invoice.delete` (default — closest semantic match; invoices are never hard-deleted, `cancel` is the destructive-equivalent action) or **NEW** `invoice.cancel` | Inferred | Yes | Medium — `invoice.delete` exists in the catalog but has no literal DELETE endpoint to attach to; recommend either renaming the catalog code's intent to "cancel" in documentation, or adding `invoice.cancel` explicitly so the code name matches the real action |

### Payments (`apps/payments`)

| Method | Endpoint | Current check | Proposed code | Doc'd? | Financial? | Risk |
|---|---|---|---|---|---|---|
| GET | `/invoices/{id}/payments` | Tenant-only | `payment.view` | **Documented** | Yes | Low |
| POST | `/invoices/{id}/payments` | Tenant-only | `payment.create` | **Documented** | Yes | Low |
| DELETE | `/payments/{id}` (void) | Tenant-only | `payment.delete` | Inferred | No (response has no amount, but the action itself is financially consequential — it recomputes the parent invoice's paid status) | Low — clean mapping, catalog code matches the action well |

### Expenses (`apps/expenses`)

| Method | Endpoint | Current check | Proposed code | Doc'd? | Financial? | Risk |
|---|---|---|---|---|---|---|
| GET | `/projects/{id}/expenses`, `/expenses/{id}` | Tenant-only | `expense.view` | **Documented** | Yes | Low |
| POST | `/projects/{id}/expenses` | Tenant-only | `expense.create` | Inferred (doc's Accountant example doesn't list "Create Expense", only "View Expense" — see §5) | Yes | Low |
| PATCH | `/expenses/{id}` (draft-only) | Tenant-only | `expense.edit` | Inferred | Yes | Low |
| DELETE | `/expenses/{id}` (draft-only) | Tenant-only | `expense.delete` | Inferred | No | Low |
| POST | `/expenses/{id}/submit` | Tenant-only, **no code today** | `expense.edit` (default — submitting your own draft is part of managing it) or **NEW** `expense.submit` | Inferred | Yes | Medium |
| POST | `/expenses/{id}/approve` | Tenant-only | `expense.approve` | Inferred (doc's worked example doesn't actually list an expense-approve action for Accountant — see §5) | Yes | **High** — this is the actual approval-chain gate (submitted→approved) an unprivileged tenant member can currently pull; the single clearest approval-workflow RBAC gap surfaced by this audit |
| POST | `/expenses/{id}/mark-paid` | Tenant-only, **no code today** | `expense.approve` (default — same final-approver authority) or **NEW** `expense.mark_paid` | Inferred | Yes | High — same reasoning as approve |

### Documents (`apps/documents`)

| Method | Endpoint | Current check | Proposed code | Doc'd? | Financial? | Risk |
|---|---|---|---|---|---|---|
| GET | `/projects/{id}/documents`, `/documents/{id}` | Tenant-only, object check present (404 via `ObjectPermission404Mixin`) | `document.view` | Inferred | No | Low |
| POST | `/projects/{id}/documents` | Tenant-only | `document.manage` | Inferred | No | Low |
| DELETE | `/documents/{id}` | Tenant-only, object check confirmed present and running before the delete side effect | `document.manage` | Inferred | No | Low — this endpoint is already correctly tenant-enforced and tested (the earlier read-only System Audit's "DELETE document gap" does not reproduce) |

### Reports (`apps/reports`) and Dashboard (`apps/dashboard`)

| Method | Endpoint | Current check | Proposed code | Doc'd? | Financial? | Risk |
|---|---|---|---|---|---|---|
| GET | `/reports/finance`, `/reports/expenses` | Tenant-only, no object-level check (ID-less aggregates) | `report.financial_access` | **Documented** | Yes | Low — these two are purely financial, clean mapping |
| GET | `/reports/dashboard` | Tenant-only, no object-level check | `report.view` **and/or** `report.financial_access` | Inferred | **Yes, extensively** — revenue/received/pending/expenses/net-profit KPIs, quotation/invoice/expense totals, per-project profitability, all in one payload | **High — genuine design decision, not a mechanical mapping.** The dashboard bundles non-financial content (recent projects, upcoming deadlines, activity feed) with heavily financial KPIs in a single response with no field-level split. Three options: **(a)** gate the whole endpoint behind `report.financial_access` — simplest, but a PM/Designer role (seeded without `financial_access`) loses the *entire* dashboard, including project/deadline data they should legitimately see; **(b)** gate behind `report.view` only and accept financial figures stay visible to every tenant member with report access until field-level filtering is built (today's actual behavior, unchanged); **(c)** split the endpoint into an operational view and a financial view (real engineering work, not a permission-mapping decision, out of scope for BE-054). **Recommend (b) as the BE-054 default** (no regression from today) with (c) filed as its own future task — but this needs an explicit decision, not silent enforcement. |

### Audit (`apps/audit`)

| Method | Endpoint | Current check | Proposed code | Doc'd? | Financial? | Risk |
|---|---|---|---|---|---|---|
| GET | `/activity-logs` | Tenant-only, no object-level check (ID-less list; `entityId` is a query filter, not a path param) | `audit.view` | Inferred | Indirect — `beforeState`/`afterState` snapshots can contain financial field values (e.g. an invoice's `total`) if the audited entity was financial | Low — clean mapping; the indirect financial exposure is a pre-existing property of the audit log itself, not something `audit.view` enforcement changes either way |

---

## 4. New code candidates surfaced by this audit (not yet in the BE-049 catalog)

None of these should be added or enforced without approval. Each has a recommended default that reuses an existing catalog code (avoids catalog growth) plus the alternative if finer delegation is wanted later:

| Action | Recommended default (reuse) | Alternative (new dedicated code) |
|---|---|---|
| `PATCH /projects/{id}/status` | `project.edit` | `project.status_manage` |
| `POST /quotations/{id}/revise` | `quotation.edit` | `quotation.revise` |
| `POST /quotations/{id}/send` | `quotation.edit` | `quotation.send` |
| `POST /quotations/{id}/reject` | `quotation.approve` | `quotation.reject` |
| `POST /invoices/{id}/send` | `invoice.edit` | `invoice.send` |
| `POST /invoices/{id}/cancel` | `invoice.delete` | `invoice.cancel` |
| `POST /expenses/{id}/submit` | `expense.edit` | `expense.submit` |
| `POST /expenses/{id}/mark-paid` | `expense.approve` | `expense.mark_paid` |

Also flagged, not an action mapping: **Products and BOQ have no "view without seeing cost/rate" code** — `product.view`/`boq.view` currently imply full financial visibility with no split available, unlike the report/dashboard split (`report.view` vs `report.financial_access`).

---

## 5. Default-role mapping check (verifying BE-049's seeded roles against this matrix)

Cross-checked `apps/users/permission_catalog.py::DEFAULT_ROLE_PERMISSIONS` against every code this matrix proposes:

- **Owner** — seeded as `"__all__"`, so it automatically covers every code in this matrix, including every new code candidate in §4 once/if added. No gap.
- **Admin** — has `role.manage`, `user.manage`, full `client.*`/`project.*`/`product.*`, `document.manage`, `audit.view`, `report.view`. **Gap found during this review:** Admin was **not** seeded with `company.view` or `company.manage` — under this matrix's mapping, a strictly-enforced Admin could not view or edit their own company's profile/settings via `GET`/`PATCH /companies/{id}`. `Permissions.md` §3 describes Admin as "manage users/roles, manage clients/projects/products, view company reports" without explicitly mentioning the company profile itself, so this may be intentional (only Owner touches company settings) — but it reads like an oversight. **Flagged for a decision, not silently fixed.**
- **Project Manager** — has `project.view/edit/manage`, `client.view`, `boq.view`, `quotation.view`, `document.view/manage`. Consistent with "view/edit assigned projects, manage tasks… view project costs (not necessarily full financial module)" — PM gets `boq.view` (project costs) but not `report.financial_access`, `invoice.*`, `payment.*`, or `expense.*`. Matches the doc's framing well.
- **Designer / Architect** — has `project.view`, `boq.view`, `quotation.view`, `document.view/manage`. Per §3 open item raised in §3's BOQ row above: Designer having `boq.view` means (under the "reuse boq.view for rate visibility" default) Designer sees full line-item rates, which sits awkwardly next to the doc's general framing that some roles "see operational data but not financial figures." Flagged, not changed.
- **Accountant / Finance** — has `client.view`, `project.view`, `boq.view`, full `quotation.*` (including `approve`), full `invoice.*`, `payment.*`, `expense.view/create/edit/approve`, `report.view/financial_access/export`. **Note:** the doc's literal worked example for Accountant does *not* list "Create Expense" or "Approve Expense" — only "View Expense." BE-049 seeded Accountant with `expense.create`/`expense.approve` anyway, as a reasonable extension consistent with Accountant owning the whole finance module, but this is itself an inference layered on top of an inference — worth a second look given expense-approve is flagged **High risk** in §3.
- **Sales / CRM User** — has `client.view/create/edit`, `project.view`, `boq.view`, `quotation.view/create`. Correctly excludes `quotation.approve` and `report.financial_access`, matching "create/view, not necessarily approve" from the doc. No gap found.
- **Site Supervisor** — deliberately not seeded (Phase 4, no module exists yet) — not applicable to this matrix.

---

## 6. BE-054 Implementation Plan (for approval — not started)

1. **Resolve open decisions first** (this document's flagged items): the Admin/`company.view` gap (§5), the dashboard financial-split question (§3), whether to add any of the §4 new codes or default to reuse, and the Accountant expense-approve extension (§5).
2. **Compatibility backstop before touching any `permission_classes`:** write a one-off management command or data migration that assigns every *existing* `CompanyMembership` with `role=None` a sensible default (most likely each company's own "Owner" role, since Owner already has every seeded code) — otherwise every pre-BE-050 membership loses all access the instant enforcement flips on, since `PermissionService` fails closed. This must run and be verified **before** any cutover PR merges, not after.
3. **Cut over module by module, each its own commit + full test pass**, in ascending risk order rather than alphabetically:
   - Lowest risk first: `documents`, `audit`, `clients`, `products`/`boq` (view/create/edit/delete only, Category-B-but-uncontested mappings).
   - Then `projects` (including the status-transition decision from §3/§4).
   - Then `roles`/`company-memberships`/`company` (RBAC-managing-itself — test carefully that Owner can never lock itself out).
   - Then the financial/workflow cluster last and most carefully: `quotations`, `invoices`, `payments`, `expenses`, `reports`, `dashboard` — these carry every **Medium/High** risk row in §3, including the expense-approval gate.
4. **Per-module cutover pattern:** replace each `*Permission.has_permission`/`has_object_permission`'s current tenant-only body with tenant check **plus** `PermissionService.has_permission(membership, code)`, where `code` is resolved per-action (list/retrieve → `.view`, create → `.create`, etc., per this matrix) — Platform Admin bypass stays unconditional per §1 unless §1's open question is resolved otherwise.
5. **Tests required per module:** (a) a membership with the correct code succeeds, (b) a membership with a role but *without* that code gets 403, (c) a membership with `role=None` gets 403 (not 500, not silently allowed), (d) Platform Admin still bypasses, (e) cross-tenant object access still returns 404 (unchanged from today, must not regress).
6. **Rollout order matches the priority list already in `BACKEND_TASKS.md`** (BE-054 is P0, already tracked) — this plan doesn't introduce new task IDs, it's the execution detail for the existing BE-054 entry.

**STOP — no code will be modified until Backend Lead approval is given on: the §5 role-mapping gaps, the §3/§4 new-code decisions, and the dashboard financial-split question.**

---

## 7. Implementation Summary (post-approval)

The Backend Lead approved this matrix and issued explicit decisions for every open item above. What follows documents what was actually built against those decisions — not a repeat of the planning rationale in §§1–6.

### 7.1 Shared enforcement mechanism

One mechanism, `apps.common.permissions.TenantScopedPermission`, replaced every previously-duplicated tenant-only permission class body (`ClientPermission`, `ProjectPermission`, `ProductCategoryPermission`, `RolePermission`, `CompanyMembershipPermission` are now thin subclasses of it, kept only for import stability). `IsPlatformAdminOrCompanyAccess` (Company's own permission class, structurally different since list/create/destroy are Platform-Admin-exclusive regardless of any code) was extended to reuse the same code-resolution helper for its retrieve/update branch rather than duplicating logic.

- **`has_permission`**: authenticated + platform-admin bypass (unchanged) + tenant resolved, **plus** the caller's active `CompanyMembership` must hold the permission code the view declares for the current action.
- **`has_object_permission`**: unchanged — platform-admin bypass, else `company_id` match. Deliberately **not** re-checking the permission code, so a same-tenant-but-wrong-permission caller gets 403 from `has_permission` while a cross-tenant caller still 404s via `ObjectPermission404Mixin` — the two failure modes stay visibly different (confirms §12/§13 items C and L are satisfied by construction, not by per-endpoint special-casing).
- **Code resolution** (`apps.common.permissions.resolve_required_permission_code`) is declarative: a view sets `permission_code` (single action) or `permission_code_map` (`{action_or_method: code}`, keyed by `view.action` for a ViewSet or `request.method.lower()` for a plain multi-method `APIView`). A view reaching `TenantScopedPermission` with neither declared **fails closed** (a `_MISSING_CODE` sentinel that never matches any real code) rather than silently passing — this is deliberate: an endpoint the cutover missed is denied, not left open.
- **`PermissionService.get_permission_codes_for_membership`** fails closed on: `membership is None`, `status != ACTIVE`, `role_id is None`, and (added during this task, see §7.6) `role.is_active is False`.

### 7.2 Privilege-escalation guard

`RoleService.assign_permissions`, `CompanyMembershipService.invite_member`, and `CompanyMembershipService.assign_role` each accept an `actor_membership` parameter. When it's not `None` (i.e., the caller isn't a platform admin), the codes being granted must be a subset of the actor's own resolved codes — a `role.manage`/`user.manage` holder can never grant (via a new role's permission set, a direct invite, or a role reassignment) any code they don't already hold themselves, including to their own membership via a crafted `roleId`. Views resolve `actor_membership` via `get_active_membership_for_request(request)`, passing `None` for a platform-admin caller (who is exempt, per the standing bypass).

### 7.3 Legacy Member (final)

- **Not** a `DEFAULT_ROLE_PERMISSIONS` entry — never auto-seeded for a new company. Exists solely as a one-time backfill target for `CompanyMembership` rows that had no role at the moment enforcement was cut over.
- Migration `0006_backfill_legacy_member_role.py`: for every company with at least one role-less `CompanyMembership` (any status — invited/active/revoked all backfilled, since a non-active one grants no access anyway regardless of role, and doing it now avoids the gap reappearing on reactivation), get-or-creates a "Legacy Member" role holding **every** catalog code, and assigns it to those memberships.
- Explicitly excludes memberships whose `user.is_superuser=True` — Platform Admin bypass must never be reachable through a tenant `Role`.
- `CompanyMembershipInviteSerializer.roleId` is now **required** (`apps/users/serializers.py`) — a new membership can never silently end up role-less (and therefore can never silently end up on "Legacy Member" either): the inviter must explicitly choose a real role every time.
- Documented as transitional technical debt in the code (migration docstring, `permission_catalog.py`'s `LEGACY_MEMBER_ROLE_NAME` comment) — not a role a company should ever knowingly assign to a new member.

### 7.4 Dashboard decision (final)

`GET /reports/dashboard` requires `report.view`, not `report.financial_access` (`apps/dashboard/views.py::DashboardView.permission_code`). `report.financial_access` remains required only for `GET /reports/finance` and `GET /reports/expenses`. **Deferred** (tracked as `BE-068` in `BACKEND_TASKS.md`): split the dashboard payload's financial fields (`kpis.totalBilledRevenue`, `.totalReceived`, `.pendingAmount`, `.totalExpenses`, `.netProfitLoss`, `recentQuotations[].total`, `pendingPayments[].total`, `overdueInvoices[].total`, `recentExpenses[].amount`, `projectProfitability[]`) from the operational fields, gating only the former with `report.financial_access`. Until then, any role holding `report.view` (which is now every seeded internal role except none — see §7.5) sees the full payload including financial figures.

### 7.5 Default role permission grants (final, resolved from `apps/users/permission_catalog.py`)

| Role | Codes | Notable |
|---|---|---|
| **Owner** | all 44 catalog codes | seeded as `"__all__"` |
| **Admin** | 21 codes: `audit.view`, `client.*`, **`company.view`, `company.manage`**, `document.*`, `product.*`, `project.*` (all 5), `report.view`, `role.*`, `user.*` | `company.view`/`company.manage` added per §7 correction (BE-049 had omitted them — a strictly-enforced Admin couldn't view their own company's profile) |
| **Project Manager** | 9 codes: `boq.view`, `client.view`, `document.view`, `document.manage`, `project.edit`, `project.manage`, `project.view`, `quotation.view`, **`report.view`** | `report.view` added — found missing during this task's own role-matrix test pass; without it PM got 403 from the dashboard, defeating §7.4's entire rationale |
| **Designer / Architect** | 6 codes: `boq.view`, `document.view`, `document.manage`, `project.view`, `quotation.view`, **`report.view`** | same `report.view` gap and fix as PM; deliberately still holds no `client.*` code at all |
| **Accountant / Finance** | 19 codes: `boq.view`, `client.view`, `expense.view`, `expense.edit`, `invoice.*` (all 4), `payment.*` (all 3), `project.view`, `quotation.*` (view/create/edit/approve), `report.export`, `report.financial_access`, `report.view` | `expense.create`/`expense.approve` **removed** per the Backend Lead's explicit instruction (undocumented beyond the doc's literal worked example); `expense.edit` and the quotation/invoice/payment/report codes beyond the literal worked example were kept — the instruction named only 2 codes to remove, not a full truncation to the 7-code worked example (documented as an explicit interpretation call, not silently assumed) |
| **Sales / CRM User** | 8 codes: `boq.view`, `client.view`, `client.create`, `client.edit`, `project.view`, `quotation.view`, `quotation.create`, **`report.view`** | same `report.view` addition |
| **Legacy Member** | all 44 catalog codes (same as Owner) | transitional only, never auto-seeded — see §7.3 |

`report.financial_access` is held **only** by Owner, Accountant, and Legacy Member — confirming financial-report access stays separate from the broadly-granted `report.view`.

### 7.6 Real bugs found and fixed during this task's own validation (not pre-existing, not from BE-049)

1. **`PermissionRepository.codes_for_role` soft-delete bug** (found via a failing service-level test on the very first implementation pass): the original query joined through the `role_permissions` reverse relation, which bypasses `RolePermission`'s soft-delete manager — a replaced/revoked grant was still counted as active. Fixed to query `RolePermission.objects` (its own soft-delete-aware manager) for permission ids first.
2. **Missing `role.is_active` check**: `PermissionService.get_permission_codes_for_membership` didn't check whether the assigned `Role` itself was active — an active membership pointing at a deactivated role kept full access. Added (test matrix item F).
3. **`report.view` missing from PM/Designer/Sales** (§7.5) — found via this task's own `test_rbac_role_matrix.py`, fixed in `permission_catalog.py` plus a backfill migration (`0008`).
4. **Two flaky test assertions** (not production bugs): `test_role_views.py` and `test_multi_company_tenant_resolution.py` asserted an exact role-list *order* that depended on `-created_at` timestamp ties between two roles created in the same test transaction, which the "id" (UUID) tie-break then resolves non-deterministically. Found when a corrupted, reused test database's failure noise was cleared and a fresh run surfaced the one genuine flake. Fixed to set-based comparisons, matching the pattern an adjacent test in the same file already used correctly.
5. **Concurrent-pytest test-database corruption** (infrastructure, not code): four parallel test-fixing agents plus this session's own validation runs collided on the same shared Postgres `test_int_projects_dev` database, producing 274 spurious failures in one run that vanished entirely once the stale database was dropped and one clean serial run was performed. Documented here as a process lesson: **never run more than one pytest process against this database at a time**, and treat any `--reuse-db` result with suspicion after a known collision.

### 7.7 Migration safety review (raised per explicit Backend Lead audit request — not yet resolved)

`0006_backfill_legacy_member_role.py`, `0007_reconcile_admin_accountant_permissions.py`, and `0008_grant_report_view_to_operational_roles.py` all identify their target role(s) **by exact `name` match** (`"Legacy Member"`, `"Admin"`, `"Accountant / Finance"`, `"Project Manager"`, `"Designer / Architect"`, `"Sales / CRM User"`). `Role` has no field distinguishing a platform-seeded default role from a company's own hand-created custom role — no `is_system_role` flag, no stable seed key, nothing but the display name, which is fully user-editable (a Company Admin can rename any role at any time via `PATCH /roles/{id}`, and can create a brand-new role under any name at all).

**Concrete risk:** a company that has — coincidentally or deliberately — named its own custom role exactly `"Admin"` would have `0007` silently add `company.view`/`company.manage` to it (additive, lower severity); a company with a custom role named exactly `"Accountant / Finance"` would have `0007` silently **revoke** `expense.create`/`expense.approve` from it if those were present (a destructive mutation of a customer-configured permission set, the more serious direction). `0006`'s risk is narrower (only touches a company at all if it already has a role-less membership at migration time) but the same name-collision mechanism applies to whatever role it finds or creates under `"Legacy Member"`.

**Present actual risk: assessed as zero today** — this project has no production deployment and no real customer-created roles yet (confirmed against `CLAUDE.md`'s MVP-phasing framing); these migrations run once, now, against dev/test data only. **Forward risk: real and unresolved** — the identical name-matching pattern would misfire the next time any of these migrations (or a similar future one) runs against a database that already has real customer-configured roles.

**Not fixed in this task**, per the explicit instruction to stop and report rather than unilaterally redesign: a proper fix would add a stable, non-user-editable identifier to `Role` (e.g. a nullable `system_key` field set only by the seeding/migration code path, never exposed to or editable via the `/roles` API) and have `0006`–`0008` (and any future reconciliation migration) match on that instead of `name`. This is a `Role` schema change with its own migration and test surface, deliberately **not** undertaken as a side effect of this validation pass — flagged as `BE-069` in `BACKEND_TASKS.md` for explicit approval before any further default-role reconciliation migration is written.

### 7.8 Security test coverage confirmation

Every item in the required test matrix (§13 of the enforcement-cutover brief) has direct coverage: correct-permission-allowed and missing-permission-403 (per-role tests across `test_rbac_role_matrix.py` and every app's view-test suite), cross-tenant-404 vs. same-tenant-unauthorized-403 as two distinct, separately-asserted outcomes (`test_role_permissions.py`, `test_membership_management_views.py`), role-less/inactive-role/revoked-membership/soft-deleted-grant fail-closed cases and immediate-revocation (`test_rbac_services.py::PermissionServiceTestCase`), permission replacement (`test_permission_replacement_old_permissions_no_longer_count`), malformed-code fail-closed (`test_malformed_or_nonexistent_permission_code_fails_closed`), privilege-escalation prevention including self-escalation via a crafted `roleId` (`test_membership_management_services.py`, `test_rbac_services.py`), platform-admin bypass, financial-access separation, dashboard operational access, and Legacy Member's unrestricted-within-tenant behavior (`test_rbac_role_matrix.py`). No coverage gap was identified requiring new tests beyond what this task already added.

`make_full_access_membership` (`apps/common/test_utils.py`) is used only for generic CRUD success-path fixtures across the pre-existing app test suites (clients/projects/products/boq/quotations/invoices/payments/expenses/documents/reports/dashboard/audit/roles/company-memberships) — every test that specifically exercises an authorization outcome (denial, escalation, tenant boundary, role-specific behavior) constructs its own narrow role/membership instead, per the Backend Lead's explicit instruction not to let the helper mask RBAC behavior.

### 7.9 Validation

- Full backend suite (fresh test database, single serial process, no `--reuse-db`): see `BACKEND_TASKS.md`'s BE-054 entry for the exact final count.
- `manage.py check`: clean. `makemigrations --check --dry-run`: no changes detected. `spectacular --fail-on-warn`: clean.
- Two spurious full-suite runs (274 and 10 apparent failures) were traced to concurrent-pytest test-database corruption (§7.6 item 5), not code defects — both vanished on a clean serial run against a freshly created test database.

### 7.10 Final endpoint coverage (every endpoint BE-054 modified)

Platform Admin bypass and tenant-gate/404-vs-403 behavior are identical on every row (§7.1) — omitted per-row to keep this readable; see §7.1 for the one shared mechanism.

| Method | Endpoint | Permission code |
|---|---|---|
| GET | `/companies/{id}` | `company.view` |
| PATCH/PUT | `/companies/{id}` | `company.manage` |
| GET/POST/DELETE `/companies`(`/{id}`) | list/create/destroy | Platform-Admin-exclusive, no code |
| GET | `/roles`, `/roles/{id}` | `role.view` |
| POST/PATCH/PUT/DELETE | `/roles`(`/{id}`) | `role.manage` |
| PUT | `/roles/{id}/permissions` | `role.manage` |
| GET | `/permissions` | none (open, bare `IsAuthenticated`) |
| GET | `/company-memberships`, `/{id}` | `user.view` |
| POST/DELETE `/company-memberships`(`/{id}`), `.../assign-role`, `.../suspend`, `.../reactivate` | `user.manage` |
| GET | `/clients`, `/clients/{id}` | `client.view` |
| POST | `/clients` | `client.create` |
| PATCH/PUT | `/clients/{id}` | `client.edit` |
| DELETE | `/clients/{id}` | `client.delete` |
| GET | `/projects`, `/projects/{id}`, `/projects/{id}/team` (GET) | `project.view` |
| POST | `/projects` | `project.create` |
| PATCH/PUT | `/projects/{id}` | `project.edit` |
| PATCH | `/projects/{id}/status` | `project.edit` (provisional mapping) |
| DELETE | `/projects/{id}` | `project.delete` |
| POST `/projects/{id}/team`, DELETE `/projects/{id}/team/{userId}` | `project.manage` |
| GET | `/product-categories`(`/{id}`), `/product-subcategories/{id}`, nested subcategory GET, `/products`(`/{id}`) | `product.view` |
| POST/PATCH/PUT/DELETE on all of the above | `product.manage` |
| GET | `/projects/{id}/boq`, `/boq/summary` | `boq.view` |
| POST | `.../boq/sections`, `.../sections/{id}/items` | `boq.create` |
| PATCH/PUT | `/boq-sections/{id}`, `/boq-items/{id}` | `boq.edit` |
| DELETE | `/boq-sections/{id}`, `/boq-items/{id}` | `boq.delete` |
| GET | `/projects/{id}/quotations`, `/quotations/{id}` | `quotation.view` |
| POST | `/projects/{id}/quotations` | `quotation.create` |
| POST | `/quotations/{id}/revise`, `.../send` | `quotation.edit` (provisional) |
| POST | `/quotations/{id}/approve`, `.../reject` | `quotation.approve` (reject is provisional) |
| GET | `/projects/{id}/invoices`, `/invoices/{id}` | `invoice.view` |
| POST | `/projects/{id}/invoices` | `invoice.create` |
| PATCH | `/invoices/{id}` | `invoice.edit` |
| POST | `/invoices/{id}/send`, `.../cancel` | `invoice.edit` (provisional) |
| GET | `/invoices/{id}/payments` | `payment.view` |
| POST | `/invoices/{id}/payments` | `payment.create` |
| DELETE | `/payments/{id}` | `payment.delete` |
| GET | `/projects/{id}/expenses`, `/expenses/{id}` | `expense.view` |
| POST | `/projects/{id}/expenses` | `expense.create` |
| PATCH | `/expenses/{id}` | `expense.edit` |
| DELETE | `/expenses/{id}` | `expense.delete` |
| POST | `/expenses/{id}/submit` | `expense.edit` (provisional) |
| POST | `/expenses/{id}/approve`, `.../mark-paid` | `expense.approve` (mark-paid is provisional) |
| GET | `/projects/{id}/documents`, `/documents/{id}` | `document.view` |
| POST/DELETE | `/projects/{id}/documents`, `/documents/{id}` | `document.manage` |
| GET | `/reports/finance`, `/reports/expenses` | `report.financial_access` |
| GET | `/reports/dashboard` | `report.view` (§7.4) |
| GET | `/activity-logs` | `audit.view` |

Every provisional mapping above matches the Backend Lead's §5 instruction exactly — no new workflow-specific permission code was introduced in this task.
