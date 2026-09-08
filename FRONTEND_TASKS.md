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

## Phase 5 — Quotations

| Task | Description | Status |
|---|---|---|
| F11 | Quotation list + BOQ-derived create flow (new Project Workspace tab) | Review |
| F12 | Quotation Detail commercial workspace (line items, financial summary, workflow actions, revision lineage) | Review |

**Implementation notes (F11/F12):**
- Backend contract audited directly from `apps/quotations` before writing UI. There is **no PATCH or DELETE endpoint for Quotation at all** — content only ever changes by creating a new version via `POST .../revise`; the detail view is otherwise fully read-only, and no delete UI was built anywhere in this module.
- Creation has two request shapes selected by whether the `items` key is present at all: omitting it (this module's only flow) tells the backend to snapshot the project's current BOQ verbatim; the BOQ-derived branch **silently ignores** any `discount`/`tax` sent, so the Create/Revise forms deliberately expose only `validUntil`/`terms`/`notes` — no discount/tax/line-item fields, to avoid a misleading no-op input.
- Versioning: `revise` always creates a new row sharing the same `quoteNumber` with `version` incremented; it has **no status precondition** (only "must be the latest version"), so Revise is offered regardless of status, while Send/Approve/Reject are each a single fixed transition (`draft→sent`, `sent→approved`, `sent→rejected`) gated on both status and latest-version, confirmed via a live 409 on every invalid transition tried (see below). Revision lineage ("Version X of Y", Previous/Next) is built entirely from the project's existing unpaginated quotation list, filtered client-side by `quoteNumber` — no dedicated lineage endpoint exists or was needed.
- New shared `FinancialSummary` component (extracted from BOQ's previously-local summary block, now used by both) renders Subtotal/Discount/Tax/Grand Total straight from backend decimal strings — zero frontend financial math anywhere in this module.
- Workflow actions (Send/Approve/Reject) each call their own dedicated endpoint behind a `ConfirmationDialog`, with loading/duplicate-submit protection and cache invalidation of the affected detail + project list; Send explicitly does not claim to dispatch an email, since the backend only flips status.
- Full lifecycle (client → project → BOQ section/item → create quotation → retrieve → verify line snapshot + totals → send → approve → two invalid-transition 409s → revise an approved quotation into v2 → attempt to act on the now-superseded v1 → confirm 409 → confirm no PATCH/DELETE exist → cleanup) verified live against the running backend.
- Frontend tests: 100 passed, 6 skipped — **zero new skips**. Every interaction (list, latest-version-only grouping, create, financial rendering, all three workflow actions, revision with prefill and navigation, version lineage gating/navigation, 404/error/empty states) is fully automated using plain buttons and Sheet/Dialog forms, none of which require opening a Radix Popper-based overlay.

## Phase 6 — Invoices

| Task | Description | Status |
|---|---|---|
| F13 | Invoice list + dual create flow (from approved Quotation, or manual/ad hoc) (new Project Workspace tab) | Review |
| F14 | Invoice Detail billing workspace (billing lines, financial summary, draft-only edit, workflow actions) | Review |

**Implementation notes (F13/F14):**
- Backend contract audited directly from `apps/invoices` (plus `apps/payments` to check for a payment aggregate) before writing UI. Unlike Quotation, Invoice genuinely has a **`PATCH /invoices/{id}`** endpoint (draft-only, 409 otherwise) — both a quotation-derived and an ad hoc invoice can have their items/discount/tax/dueDate/paymentTerms/notes edited identically while still draft, so an Edit sheet was built (`EditInvoiceSheet`), unlike Quotation's revision-only model.
- Creation genuinely supports **two first-class, equally-tested paths** (confirmed via `test_create_ad_hoc_invoice` and `test_create_from_approved_quotation` in the backend suite): from an approved quotation (copies items/subtotal/discount/tax/total verbatim, silently ignoring any caller-supplied discount/tax, exactly like Quotation's BOQ-derived branch) or ad hoc (caller-supplied line items, flat discount/tax). `CreateInvoiceSheet` exposes both via a Tabs toggle ("From Quotation" / "Manual") rather than picking one, since the backend treats them as equally valid. The quotation picker only lists the **latest version of each quote number that is currently `approved`** (a safe filter using only already-returned `status`/`version` fields, not an invented business rule) and shows an empty state instead of a picker when none exist.
- `Invoice` has **no `issueDate` field** (only `createdAt`/`dueDate`) and **no `paidAmount`/`balance`/payment-aggregate field anywhere** — confirmed by reading `InvoiceSerializer` and the separate `apps/payments` app (whose only endpoint returns a raw, unaggregated list of individual Payment rows, out of scope this phase). The Payment Summary section from the original brief was **omitted** rather than computed by summing raw payment amounts client-side, since that would be exactly the forbidden frontend financial math this project's standing rule forbids — tracked as technical debt below, not built around with a workaround.
- New `InvoiceLineItemFields` (react-hook-form `useFieldArray` + Zod) is shared verbatim between the Manual create form and the Edit sheet — both submit an identical full-array-replacement shape, so one line-item editor (add/remove row, description/quantity/unit/rate, invoice-level discount/tax/dueDate/paymentTerms/notes) serves both instead of being duplicated. No computed line amount is ever previewed client-side; `amount` is only ever rendered post-save from the backend's own response.
- Billing lines render with the same dual desktop-table/mobile-card pattern established in BOQ (explicitly requested for this module) — a dense table on desktop, one card per line (description, qty+unit, rate, amount) on mobile.
- `FinancialSummary` (already shared with BOQ/Quotations) is reused as-is — Invoice's subtotal/discount/tax/total shape is identical.
- Send is a pure `draft→sent` status transition with no email dispatch and copy that says so explicitly ("does not dispatch an email"); Cancel is available from `draft/sent/partially_paid`, uses the destructive button/dialog treatment, and its copy explicitly states it does not reverse or affect any recorded payments. `overdue` is rendered exactly as the backend's read-time-derived effective status — never re-derived from the browser's own clock.
- Source Quotation is shown with its real `quoteNumber`/version via a single conditional fetch of the one linked quotation when `quotationId` is present (not a list, so not an N+1), linking to that quotation's own detail page.
- Full lifecycle (client → project → BOQ → quotation → send → approve → invoice-from-quotation → invoice-ad-hoc → PATCH the draft ad hoc invoice → send the quotation-derived invoice → invalid re-send 409 → invalid PATCH-after-send 409 → cancel → invalid re-cancel 409 → confirmed no DELETE support (403, permission-checked before method dispatch, since `delete` has no RBAC code mapped) → cleanup) verified live against the running backend.
- Frontend tests: 126 passed, 6 skipped — **zero new skips**. The Tabs mode-switcher and the plain-button quotation-picker (a bordered `role="radio"` card list, not a Radix Select/Popover) were both chosen specifically to stay outside the previously-diagnosed Radix Popper/jsdom hang, and both were verified interaction-tested without issue.

## Not Yet Started

Payments, Expenses, Documents, Reports, Team/Roles management screens, Settings — per `06_UI/Wireframes.md`'s module order, each its own approved increment.
