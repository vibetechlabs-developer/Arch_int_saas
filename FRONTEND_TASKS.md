# Frontend Tasks

Tracks the frontend build sequence against `06_UI/Wireframes.md`'s module order, mirroring `BACKEND_TASKS.md`'s convention: implemented work is marked **Review** by the implementer and moved to **Done** only by the Frontend/Backend Lead's own sign-off, never self-approved.

## Status Legend

`Not Started` → `Review` (implemented, awaiting Lead approval) → `Done` (Lead-approved)

## Phase 1 — Foundation, Shell, Login, Dashboard, Clients

Marked **Done** per Frontend Lead's explicit approval ("Frontend Phase 1 is technically approved").

| Task | Description | Status |
|---|---|---|
| F0 | Frontend architecture / ground-truth audit | Done |
| F1 | Premium design-system foundation ("Architectural Warmth" — tokens, shadcn-style primitives) | Done |
| F2 | Premium application shell (sidebar, header, command palette, mobile nav, notification drawer) | Done |
| F3 | Login screen (real `/auth/login`, silent-refresh axios client) | Done |
| F4 | Dashboard (real `GET /reports/dashboard`) | Done |
| F5 | Clients module (list, create/edit, detail, delete — server-side search/sort/pagination) | Done |

Commits: `eca619b` (F0–F4 foundation), `4892d2c` (F5 Clients).

## Phase 2 — Projects

| Task | Description | Status |
|---|---|---|
| F6 | Projects list (server-driven status/client/priority filters, no free-text search per backend contract) | Review |
| F7 | Project workspace (persistent header + Overview/Team tabs via nested routes, status transition, team add/remove) | Review |

Commit: `e536c1c` (`feat(frontend): add project workspace and team management`).

**Implementation notes (F6/F7):**
- Backend contract audited directly from `apps/projects` (models/serializers/services/views) before writing UI — see the commit message and PROJECTS FRONTEND REPORT for the full contract.
- `Project` has no `description` field — omitted from Overview, not invented.
- `priority` is documented as deliberately unconstrained free text (no enum) — rendered as a plain input/filter, not a fabricated dropdown.
- Allowed status transitions are server-only business logic (`get_allowed_next_statuses`), never exposed via the API — the status-change UI offers every status and treats the backend's 409 as authoritative, per explicit instruction not to duplicate business rules on the frontend.
- New shared `Combobox` primitive (Popover + cmdk) backs both the Client selector (Project create/edit) and a company-member selector (Add Team Member, sourced from the real `GET /company-memberships` endpoint).
- Full CRUD + status-transition + team lifecycle verified live against the running backend (see commit message); test data cleaned up afterward.
- Frontend tests: 35 passed, 6 explicitly skipped (all six are Radix Select/Popover/DropdownMenu open-and-interact flows that hang in this project's jsdom+Jest+Node combination — a reproduced environment issue, not an app defect; each skip cites the diagnosis and the live-backend flow that verifies the same behavior independently).

## Phase 3 — Product Catalog

| Task | Description | Status |
|---|---|---|
| F8 | Product Catalog (list, create/edit, detail — server-driven category/subcategory/status filters, no free-text search per backend contract) | Review |
| F9 | Product Category / Subcategory management (`/settings/product-categories`, expandable-row taxonomy editor) | Review |

Commit: `1a5042b` (`feat(frontend): implement product catalog experience`).

**Implementation notes (F8/F9):**
- Backend contract audited directly from `apps/products` before writing UI. Only two RBAC codes exist (`product.view`/`product.manage`, no separate create/edit/delete). No `search` param exists anywhere in this app. `Product.imageUrl` is a plain URL field — no upload endpoint exists, so no upload UI was built. Subcategory listing is nested under its category as a plain unpaginated array (`GET /product-categories/{id}/subcategories`), unlike every other list endpoint in the app.
- Category → Subcategory is a dependent-selector pair in both the product filter bar and the create form: changing/clearing the category clears the subcategory, and the subcategory picker is disabled until a category is chosen.
- Category/Subcategory management uses an expandable-row list rather than `DataTable`, since neither is paginated or expected to grow large — a category row expands in place to reveal its subcategories.
- New shared `Money` component (tabular numerals, backend decimal strings only — never JS float math) and `ProductThumbnail` (broken-image fallback, no fake stock imagery).
- Full catalog lifecycle (category → subcategory → product → retrieve → update → filter → both 409 delete-guards → cleanup) verified live against the running backend.
- Frontend tests: 58 passed, 6 skipped — **the skip count did not increase** from the Projects module. Every new test was deliberately designed to avoid the previously-diagnosed Radix Select/Popover/DropdownMenu jsdom hang (Category/Subcategory forms are plain-text dialogs with no combobox; Product edit shows category/subcategory as static text). The few scenarios that genuinely require opening a combobox via the UI (category/subcategory list filters, create-with-a-real-picked-subcategory, category-change-clears-subcategory) were not automated as a 7th+ skip; they're covered by the live API smoke test instead, per the explicit instruction not to grow the skip count.

## Phase 4 — BOQ Workspace

| Task | Description | Status |
|---|---|---|
| F10 | BOQ Workspace (new Project Workspace tab — sections, items, backend-authoritative summary totals) | Review |

Commit: `a767a6e` (`feat(frontend): implement project BOQ workspace`).

**Implementation notes (F10):**
- Backend contract audited directly from `apps/boq` before writing UI. `GET /projects/{id}/boq` returns the entire section+item tree in one call (no pagination anywhere in this app); the BOQ auto-creates on first access (no POST endpoint); sections have no reorder API, so no drag-and-drop was built. The exact product→item default mapping was confirmed from `BOQItemService` before writing the prefill logic: `description ← product.name`, `unit ← product.unit`, `rate ← product.defaultSellingRate` (**not** `defaultCost`), `tax ← product.taxRate`.
- All financial totals (subtotal/discount/tax/grand total) come from the backend's `GET .../boq/summary` — zero tax/discount/rounding math computed on the frontend. Per-section totals were deliberately **not** built (the backend provides none), to avoid any frontend financial computation whatsoever; only plain item *counts* (integers) are shown at the section level.
- Section and item row actions use plain inline icon buttons rather than a `DropdownMenu` — both a better fit for a fast, dense estimation workspace and a deliberate way to avoid the previously-diagnosed Radix DropdownMenu/Select/Popover jsdom hang for this module's own new code.
- Full lifecycle (project/category/subcategory/product → BOQ → section → product-referenced item → summary → edit section/item → 409 delete-guard → delete → cleanup) verified live against the running backend.
- Frontend tests: 79 passed, 6 skipped — **zero new skips**. Every BOQ-specific interaction (including section/item delete, product-combobox integration, decimal-string preservation, summary refetch after mutation, and mobile item-card rendering) is fully automated; none required a skip.

## Not Yet Started

Quotations, Invoices, Payments, Expenses, Documents, Reports, Team/Roles management screens, Settings — per `06_UI/Wireframes.md`'s module order, each its own approved increment.
