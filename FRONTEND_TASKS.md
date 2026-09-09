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

## Phase 7 — Payments

| Task | Description | Status |
|---|---|---|
| F15 | Payment recording + history (integrated into Invoice detail, not a standalone module) | Review |
| F16 | Invoice Payment Experience (Payment History section, Record Payment sheet, void workflow) | Review |

**Implementation notes (F15/F16):**
- Backend contract audited directly from `apps/payments` (models/urls/serializers/views/services/selectors/repositories/validators/tests), plus `apps/reports` to rule out a reusable aggregate. Endpoints are `GET/POST /invoices/{id}/payments` and `DELETE /payments/{id}` (void) only — **no GET single-payment endpoint and no PATCH/PUT anywhere**, so no Edit action and no `/payments/:paymentId` route were built.
- **PAYMENT AGGREGATE API GAP: YES.** No endpoint anywhere returns a per-invoice `paidAmount`/`outstandingAmount`. `PaymentRepository.sum_active_amount_for_invoice` exists but is server-internal only (used by `InvoiceService.recompute_status_from_payments`), never serialized; `/reports/finance`'s `outstanding` figure is a company-wide overdue aggregate, not a per-invoice value. Per standing instruction, this was **not** worked around by summing `sum(payments.amount)` or computing `total − sum(payments)` client-side — no Payment Summary component exists; the invoice's own (already-authoritative) status badge is the only "is this paid" signal shown. Recommended backend follow-up: add `paidAmount`/`outstandingAmount` to `InvoiceSerializer`, computed the same way `recompute_status_from_payments` already does internally.
- `method` has **no backend enum** (`Payment.method` docstring: "no documented value domain") — rendered as a plain free-text `Input`, not a Select of invented options (Cash/UPI/Bank Transfer/etc., none of which exist server-side).
- **Overpayment is genuinely allowed** — confirmed by reading `PaymentService.create_payment` (only `require_positive_amount` validates the amount; nothing compares it to any outstanding balance) and verified live (a payment pushing paid-total to 700 against a 500 total returned 201, not a 409). The Record Payment form therefore never blocks, warns, or silently caps an entered amount.
- Payments are **append-only with void, not edit/delete/reverse** — `DELETE /payments/{id}` soft-deletes ("voids") and triggers `InvoiceService.recompute_status_from_payments` from the remaining active payments; represented as a "Void" action (`Undo2` icon, destructive `ConfirmationDialog`) that explicitly says "audit-logged, not deleted."
- No project-scoped `/projects/:projectId/payments` route and no Payments tab were added to Project Workspace — the backend has no project-scoped payment-listing endpoint, only invoice-scoped, so a project-level page would have nothing real to call.
- `PaymentHistory` (billing-lines-style dual desktop-table/mobile-card list) and `RecordPaymentSheet` are both embedded directly into `InvoiceDetailPage` — Date/Method/Reference/Amount columns, `Money`/tabular-nums, right-aligned amount. `Record Payment` is hidden exactly when the backend would reject it (`draft`/`cancelled`, mirroring `UNPAYABLE_INVOICE_STATUSES` precisely) and deliberately stays visible on a `paid` invoice, since the backend does not reject further payments there.
- Every Payment mutation (record, void) invalidates the invoice's payment list, the Invoice detail query (so status transitions like `sent→partially_paid→paid` render from the real refetched response, never recreated client-side), and that invoice's project invoice-list cache — nothing broader.
- Full lifecycle (client → project → BOQ → quotation → send → approve → invoice → attempted payment on draft (409) → send invoice → partial payment → verify `partially_paid` → overpayment accepted (`paid`, no rejection) → void the first payment (status stays `paid` since the second payment alone still covers the total) → confirmed voided payment excluded from the list → confirmed no `GET /payments/{id}` exists (405) → cleanup) verified live against the running backend.
- Frontend tests: 142 passed, 6 skipped — **zero new skips**.

## Phase 8 — Expenses

| Task | Description | Status |
|---|---|---|
| F17 | Expense list with real server-side filters (category/vendor/status/date range) + create (new Project Workspace tab) | Review |
| F18 | Project Expense Workspace (Expense detail route, edit, delete, submit/approve/mark-paid workflow) | Review |

**Implementation notes (F17/F18):**
- Backend contract audited directly from `apps/expenses` (models/urls/serializers/views/services/selectors/repositories/validators/tests), plus `apps/reports` for a possible aggregate. Workflow is strictly linear — `draft → submitted → approved → paid` — with **no reject/cancel state and no reject endpoint at all** (confirmed both in the enum and live: `POST .../reject` 404s). Delete and PATCH are both draft-only, 409 otherwise, confirmed live.
- **No `ExpenseType`/category model exists anywhere** — `category` (like `vendor` and `paymentMethod`) is unconstrained free text, so all three are plain `Input`s on create/edit and plain exact-match text filters on the list, never a hardcoded Select of invented values (no "Materials/Labour/Travel" dropdown).
- **No `paymentDate`, no reference/invoice-number field, and mark-paid takes no payload** — it's a pure `approved → paid` status flip with nothing captured. Expense's "paid" is entirely separate from the Payments module; it does not create a Payment record or touch any Invoice.
- **Authoritative summary: `GET /reports/expenses` exists** (real, `Sum("amount")`-backed category/project/vendor/employee/date breakdown, accepts `?projectId=`) but was deliberately **not embedded** in the Expense workspace — it requires `report.financial_access`, a materially more privileged permission code than any `expense.*` code, so surfacing it inline would make a "core" widget silently vanish for most users who can otherwise fully use expenses. Noted as a future Reports-module enhancement rather than built here, per the explicit "don't build it merely because the endpoint exists" guidance.
- Employee selection reuses the existing `CompanyMemberCombobox` (same component/validator ProjectTeam's `assignedTo` uses) — unlike BOQItemFormSheet's static-in-edit-mode product reference, Expense's `employeeId` genuinely stays mutable via PATCH while draft, so the combobox stays interactive in both create and edit.
- `ExpenseFilterBar` adds real server-side filtering (category/vendor/status/date-range) to a project-scoped list for the first time in this app (Quotations/Invoices/Payments are all unfiltered) — each filter change re-keys the TanStack Query cache rather than filtering an already-loaded array. Category/vendor use a short debounce to avoid a request per keystroke; the Status Select's open-and-choose interaction is (consistent with every prior module) not exercised via `userEvent` in tests, so the date-range inputs (plain `<input type="date">`) carry that coverage instead.
- Async mutation safety: every new Expense mutation form uses `mutation.isPending` (not `isSubmitting`) for its submit-button disabled/loading state, applying the pattern identified during the Payments phase from the start rather than retrofitting it.
- Full lifecycle (client → project → create expense → retrieve → edit while draft → invalid approve-before-submit (409) → submit → invalid PATCH-after-submit (409) → invalid delete-after-submit (409) → approve → mark paid → confirmed no reject endpoint (404) → confirmed delete is genuinely draft-only by attempting it on the now-paid expense (409) → category/status filters verified → cleanup via project cascade, since a paid expense cannot itself be deleted) verified live against the running backend.
- Frontend tests: 174 passed, 6 skipped — **zero new skips**.

## Phase 9 — Documents

| Task | Description | Status |
|---|---|---|
| F19 | Document list with register-by-URL create (new Project Workspace tab) | Review |
| F20 | Project Document Workspace (open/delete actions, restrained file-type iconography, image thumbnails) | Review |

**Implementation notes (F19/F20):**
- Backend contract audited directly from `apps/documents` (models/urls/serializers/views/services/selectors/repositories/validators/tests). The entire field set is `id, companyId, projectId, entityType, entityId, fileUrl, version, uploadedById, uploadedByName, uploadedAt` — **no title, description, category, MIME type, file size, or original filename exist anywhere**, and **no PATCH endpoint exists at all** (confirmed live: 403, since `patch` has no RBAC code mapped, same permission-checked-before-dispatch behavior found on Invoice's DELETE earlier). No 409 case exists for Document anywhere in this app — delete has no constraints at all.
- **No file upload endpoint exists anywhere in this codebase** (confirmed verbatim in the model's own docstring and by the create serializer accepting only `fileUrl`) — a document is registered by URL, the exact same pattern already established for Payment/Expense receipts and Product images. `RegisterDocumentSheet` therefore has exactly one field. No `<input type="file">`, no dropzone, no upload progress UI were built, since there is nothing to upload to.
- **Versioning nuance, confirmed live**: `version` auto-increments as `max(version for this exact (entityType, entityId) pair) + 1`. Since every document from this workspace defaults to the shared target `(entityType="project", entityId=<project id>)`, `version` is really a sequential counter across *all* of a project's general documents, not "revisions of the same file" — verified live (uploading a second, unrelated file gave it `version: 2`). There is no upload-new-version endpoint, no parent-document link, and no "latest version" flag, so no version-history UI was built; the raw number is shown plainly (`v1`, `v2`, …) as real data, not as a revision-navigation feature.
- **Categories: not supported** (no field/enum/model). **Folders: not supported** (no field). **File size: not supported** (no bytes field returned — no size is ever shown, fabricated, or estimated). A filename is derived presentationally from the URL's last path segment (`displayFileName`) purely for display, explicitly never treated as validated or security-relevant data; the same derivation feeds a restrained, one-family (lucide) file-type icon by extension.
- **No preview beyond a best-effort image thumbnail** — `fileUrl` is an arbitrary external URL uploaded out-of-band with no backend-confirmed access pattern, so there is no PDF iframe embed and no assumption that any URL is authenticated-browser-accessible. Image-extension URLs get a small `<img>` thumbnail with a React-state (not DOM-mutating) broken-image fallback; everything else gets an icon plus a plain `target="_blank" rel="noreferrer"` "Open" link — never a fabricated "Download" semantic, since the API gives no dedicated download endpoint.
- No `/documents/:documentId` detail route was built — with no editable metadata and every field already visible in the list row, a dedicated route would exist "just for two fields," which the brief explicitly warns against.
- Security review: no `dangerouslySetInnerHTML`, no `javascript:`-link risk, no object-URL creation/cleanup needed (no blob URLs used); the derived filename is always rendered as plain JSX text (auto-escaped) — verified with a test asserting a filename containing literal `<img onerror=...>` text renders as inert text, not markup.
- Full lifecycle (client → project → register a document → retrieve → list → re-upload to the same default target and confirm version increments to 2 → missing-`fileUrl` 400 → confirmed no PATCH exists (403) → delete → confirmed 404 → cleanup) verified live against the running backend.
- Frontend tests: 190 passed, 6 skipped — **zero new skips**.

## Phase 10 — Activity Log

| Task | Description | Status |
|---|---|---|
| F21 | Activity Log | **Blocked** |
| F22 | Project Activity Timeline | **Blocked** |

**Why blocked (full detail in the ACTIVITY FRONTEND REPORT delivered with this entry):** the only backend surface (`GET /activity-logs`, built directly over the `AuditLog` table — there is no separate, safer Activity model) has no `project_id` field at all, so there is no way to query "everything that happened in project X" — only one exact `(entityType, entityId)` pair at a time, or the whole tenant. It also carries no entity display name (a bare `entityId` UUID is all that identifies a non-project entity) and returns internal audit fields (`ipAddress`, `requestId`, raw `before/afterState` JSON) unredacted. Worse, its permission code (`audit.view`) is seeded **only to Owner and Admin** in `permission_catalog.py` — Project Manager, Designer, Accountant, and Sales (the roles who actually live inside Project Workspace) don't hold it, so the tab as specified would 403 for its intended everyday audience. Dashboard's existing "Recent Activity" section already proves the *safe-subset rendering* half of this is solvable (it renders only `actorUserName`/`action`/`entityType`/`createdAt` from this same shape) — the blocker is purely the missing project-scoping and the admin-only gate, not an inability to format the data safely. No Django was modified; no workaround (client-side aggregation across per-entity queries, or parsing internal fields) was attempted. Recommended smallest backend change: add a `project_id` field to `AuditLog` (populated the same way `entity_type`/`entity_id` already are) plus a `GET /projects/{id}/activity` endpoint gated by an ordinary project permission (e.g. `project.view`) that also resolves a human-readable entity label instead of a bare UUID.

## Phase 11 — Reports

| Task | Description | Status |
|---|---|---|
| F23 | Reports (Finance + Expense breakdown, company-wide) | Review |
| F24 | Financial / Operational Reporting Experience | Review |

**Implementation notes (F23/F24):**
- Backend contract audited directly from `apps/reports` (serializers/services/views/urls/tests) and cross-referenced against `apps/dashboard` and `permission_catalog.py`. Exactly **two** report endpoints exist: `GET /reports/finance` (revenue/received/receivables/outstanding/expenses/profitLoss, scoped by optional `projectId`/`dateFrom`/`dateTo`) and `GET /reports/expenses` (byCategory/byProject/byVendor/byEmployee/byDate breakdowns, same filters). **Both are gated by `report.financial_access`**, not `report.view` — this is stricter than Dashboard (gated by the more common `report.view`) and, per `permission_catalog.py`'s `DEFAULT_ROLE_PERMISSIONS`, is seeded only to Owner and Accountant/Finance — **not even Admin**. There is no separate Project/Client/Sales report endpoint, no pagination, no export endpoint (despite a `report.export` permission code existing in the catalog — an unused permission, not a missing frontend feature), and no company-currency endpoint (existing known debt, unchanged).
- Because both real endpoints share the same filter shape, one `ReportFilterBar` (Project select + From/To date inputs) drives both panels rather than duplicating controls. The Project select is a plain dropdown loaded once at `pageSize=100` (Project has no `search` param — the same established gap as Product/Category), matching `ProductCombobox`'s precedent rather than introducing a new pattern.
- `FinanceReportPanel` renders all six Decimal fields via `<Money>` only — no `parseFloat`/`.reduce()` anywhere; the profit/loss tone (success/danger) is chosen by reading the Decimal string's own leading `-` character, never by converting it to a number for the displayed value. `ExpenseReportPanel` shows the five breakdowns as tabbed tables (Category/Project/Vendor/Employee/Date) and deliberately renders **no summed footer total** — the breakdown includes every non-deleted expense regardless of `approval_status`, a broader scope than `FinanceReportService`'s approved/paid-only `expenses` figure, so a client-computed sum would not equal, and would be mistaken for, that authoritative figure.
- A 403 on either endpoint renders a dedicated `RestrictedState` ("Restricted" + the backend's own message, no retry action) rather than the generic `ErrorState` — retrying changes nothing until the caller's role is granted `report.financial_access`. Each panel manages its own query/error state independently, so one section's 403 never blanks the other.
- Reports was added to primary sidebar navigation (Commercial group, alongside Products) and to the Command Palette's "Go to" group. Dashboard was left untouched — Reports is the filtered, drill-down companion to Dashboard's fixed, unfiltered KPI snapshot, not a duplicate of it; the only genuinely new figure Reports surfaces is `outstanding` (the overdue-only subset of receivables), which Dashboard does not show.
- Frontend tests: 218 passed, 6 skipped — **zero new skips**. TypeScript: PASS. Build: PASS.
- Live API smoke test: not run — no local backend session was available in this phase; the contract above was established entirely via direct backend code reading (services/serializers/views/tests), consistent with how the Activity Log phase's blocker was also established without live calls.

## Phase 11b — Tracker Reconciliation (shipped, previously untracked)

Two phases shipped in prior sessions with no `FRONTEND_TASKS.md` entry — reconciled here per the Admin & Settings task's explicit instruction, statuses unchanged from their own commits.

| Task | Description | Status |
|---|---|---|
| F25 | Product Image Upload (real multipart `POST /products/images/upload`, `ProductImagePicker`, replace/remove lifecycle) | Review |
| F26 | Navigation discoverability fixes (sidebar active-state cross-path matching, breadcrumb project-context for Quotation/Invoice/Expense) | Review |

Commits: `c5094e2`/`df3036b` (F25), `83cf909` (F26).

## Phase 12 — Admin & Settings

| Task | Description | Status |
|---|---|---|
| F27 | Settings shell (`/settings/*` nested layout, grouped internal nav, landing page) | Review |
| F28 | Company Settings (`/settings/company` — view/edit name, currency, GSTIN) | Review |
| F29 | Member management (`/settings/members` — list, invite, view detail, change role, suspend, reactivate, remove) | Review |
| F30 | Role management (`/settings/roles` — list, create, edit metadata, delete, initial permission assignment on create) | Review |
| F31 | Permission catalog (`/settings/permissions`, read-only, grouped by module) | Review |
| F32 | Profile (`/settings/profile`, read-only) | Review |
| F33 | Security (`/settings/security` — send-password-reset-email action only) | Review |
| F34 | Navigation integration (Settings sidebar entry, Header user-menu Profile/Settings links + workspace name, breadcrumbs, Command Palette entries) | Review |

**Implementation notes (F27–F34):**
- Backend contract audited directly from `apps/company`, `apps/users`, `apps/authentication` (models/serializers/views/urls/services) before writing any UI — see the full ADMIN API CONTRACT delivered with this phase's report.
- **No "get current company" endpoint exists.** `GET /auth/memberships` (never previously called anywhere in the frontend) is the only source of the caller's own `companyId`; a new `useCurrentCompanyId()` hook resolves it from the first active membership, matching the app's existing single-membership assumption (no workspace switcher was built — the current company's name is now shown in the Header user menu, but switching between multiple memberships remains out of scope, flagged below).
- **`Company` has no address, logo, or timezone field** — only `name`/`status`/`currency`/`gstNumber`/`settings` exist. Company Settings exposes exactly those (minus `status`, which the backend silently no-ops for non-platform-admins rather than erroring — shown read-only instead of as a misleading control).
- **BLOCKED, not built: editing an existing role's permissions.** `PUT /roles/{id}/permissions` is a full-replacement write with no corresponding read endpoint anywhere in the backend (`RoleSerializer` never includes granted codes, and there is no `GET /roles/{id}/permissions`). A checkbox editor for an already-configured role would have no way to show which codes are currently granted, risking a blind save silently wiping real access. Per the "stop and document" rule, this was not built; the Roles page's Permissions section instead documents the exact gap inline. Permission assignment **is** fully supported for a **newly created** role only, where "nothing granted yet" is accurate rather than assumed (`AssignInitialPermissionsDialog`, chained automatically from Create Role).
- **No self-action protection exists server-side** for suspend/remove (`CompanyMembershipService` has no actor-vs-target check anywhere) — the Members page disables Suspend and Remove on the current user's own row as a client-side safety courtesy, since the backend will not stop it.
- **No profile-edit or in-session change-password endpoint exists.** Profile is read-only by design (not a stripped-down form). Security ships exactly one real capability — sending a password-reset email via the existing (previously frontend-unused) `POST /auth/forgot-password`, pre-targeted at the caller's own address — and explicitly states that 2FA/session-management aren't available, rather than showing dead controls.
- Product Categories (`/settings/product-categories`, shipped in F9) was moved into the new Settings IA: the primary sidebar's Products item no longer special-cases it via `matchPaths` — visiting it now correctly activates the "Settings" sidebar entry, since it's a settings concern, not a Products-workflow one. `RestrictedState` was promoted from `components/reports/` to `components/common/` (Reports' own imports updated) since Settings pages now share it for 403s.
- `StatusBadge`'s semantic map gained `invited`→info/`revoked`→danger for `CompanyMembershipStatus` (`active` already existed, shared with Product's own `active` status).
- **KNOWN ENVIRONMENT LIMITATION, confirmed this phase, extending the existing 6-skip Radix+jsdom baseline**: an isolated minimal reproduction (a bare Radix `DropdownMenu` and a bare Radix `Select`, zero app code) confirmed both hang indefinitely on `userEvent.click` of their trigger in this Jest/jsdom setup, with or without `pointerEventsCheck: 0`. Per the same convention established in `ProductFormSheet.test.tsx`, tests requiring one of these to open were not written (not skipped) — see `MembersPage.test.tsx`/`RolesPage.test.tsx`'s own docstrings for the exact list of untested flows (invite-form role selection, and every DropdownMenu-gated row action: change role, suspend, reactivate, remove, edit role, delete role) and a plausible root cause worth a dedicated look: `package.json` pins `jest@^29.7.0` against `jest-environment-jsdom@^30.5.1`, a major-version mismatch.
- Full lifecycle exercised via automated tests where the above limitation allows (list/empty/403/detail-view/create-role/permission-assignment-on-create/409-conflict flows); the DropdownMenu-gated mutations (change role, suspend, reactivate, remove, edit, delete) were **not** live-smoke-tested against a running backend in this phase either — no local backend session was available, consistent with how F23/F24 was also established via code-reading alone.
- Frontend tests: 265 total, 259 passed, **6 skipped — unchanged baseline** (26 new tests added, 0 new skips). TypeScript: PASS. Build: PASS.
- Visual QA: **PENDING** — no browser tooling available in this environment; see the phase's final report.

**Remaining Admin/Settings gaps (flagged, not invented around):**
- No `GET /auth/permissions`-style "my resolved permission codes" endpoint — the frontend cannot hide Settings sections/buttons by permission, only react to a 403 (matches the Reports precedent, not a regression).
- No `Role.system_key`/protected-role flag (pre-existing `BE-069` debt) — Roles page never invents edit/delete restrictions from role names; last-owner protection remains unbuilt for the same reason.
- ~~No workspace/company switcher~~ and ~~role delete does not revoke access~~ — both closed in Phase 15 below.

## Phase 13 — Add User Management

| Task | Description | Status |
|---|---|---|
| F35 | Add User workflow (replaces Invite Member as the Members page's primary CTA) — new `AddUserSheet`, `/company-memberships/add-user` API wiring | Review |
| F36 | Set Password page (`/reset-password`) — previously missing entirely; consumes the same token as both forgot-password recovery and Add User account activation | Review |

**Implementation notes (F35/F36):**
- "Invite Member" could only link an existing global User account (404 on an unknown email) — genuinely insufficient for a company admin who wants to bring a brand-new person into the product. `AddUserSheet` replaces it entirely (component and its unused test surface deleted, not left as dead/duplicate code) as the Members page's one primary CTA, per explicit product direction that Add User is a strict superset of Invite Member's capability.
- New `POST /company-memberships/add-user` (backend contract audited directly, see `BACKEND_TASKS.md` BE-071): request `{email, name, roleId}`, response `{membership, userCreated, activationRequired}`. The backend decides whether a new account was created or an existing one linked — the frontend never needs to know or ask, matching Phase 20's explicit "don't reveal internal account state" guidance. Toast copy is conditional on the real `activationRequired` flag ("User added. An account setup email was sent." vs. "User added successfully.") — never a claim the frontend can't back with a real response field.
- **Real, previously-missing gap closed**: no `/reset-password` route existed anywhere in the frontend despite the backend supporting token-based password reset since Sprint 1 (confirmed by a full read of the old route table) — without it, a newly added user had no way to ever complete account setup and log in. New `SetPasswordPage` serves both that gap and, incidentally, the pre-existing (also previously unbuilt) forgot-password recovery flow, since the backend endpoint treats both token sources identically.
- Duplicate-membership 409 and per-field 400s are mapped onto the form the same way `CompanyMembershipInviteSerializer` errors already were, matching established convention (`RoleFormSheet`/old `InviteMemberSheet` pattern).
- Command Palette's "Add Member" entry updated to "Add User" (`?addUser=true`, was `?invite=true`).
- Frontend tests: 272 total, 266 passed, **6 skipped — unchanged baseline** (14 new tests added: `MembersPage.test.tsx` extended, new `SetPasswordPage.test.tsx`). Role-Select-driven submission of the Add User form itself remains untested here for the same documented Radix+jsdom environment limitation as Phase 12 — field validation (name/email/role all required, shown before any API call) is covered without needing to open the Select. TypeScript: PASS. Build: PASS.
- Visual QA: **PENDING** — no browser tooling available in this environment.

**Remaining gap:** self/last-owner safety is now backend-enforced (see BE-071) — the frontend's existing client-side disabling of Suspend/Remove on one's own row (Phase 12) is now a UX courtesy on top of real server enforcement, not the only protection.

## Phase 14 — Role Permission Management (completes Roles & Permissions)

| Task | Description | Status |
|---|---|---|
| F37 | Manage Permissions on any role (not just newly-created ones) — pre-checks real persisted grants via new `GET /roles/{id}/permissions` | Review |

**Implementation notes (F37):**
- Closes the exact gap Phase 12's own report flagged: `AssignInitialPermissionsDialog` (blank-only, new-role-only) is replaced by `ManagePermissionsDialog` — same UI, but now fetches the role's real current grants (`getRolePermissions`, `BACKEND_TASKS.md` BE-072) before rendering, so every checkbox reflects actual server state rather than assuming empty. The "Roles page can't edit an existing role's permissions" `Alert` banner is removed — it's no longer true.
- "Manage permissions" is now a row action on every role in the Roles table (previously reachable only immediately after Create Role).
- **No state leakage between roles**: switching which role the dialog is pointed at re-keys the `getRolePermissions` query (`roleKeys.permissions(roleId)`) and a `useEffect` re-syncs local checkbox state from the freshly-fetched grants every time — verified directly (`ManagePermissionsDialog.test.tsx`, Role A → Role B test).
- **Save submits the complete edited set**, matching the backend's confirmed full-replacement semantics — never just the checkboxes the admin touched this session (verified: an existing grant not touched by the admin is still included in the submitted array).
- **Reopen reflects persisted server state**, not stale local state — verified by mocking the grants endpoint to return updated data post-save, then closing/reopening the dialog and asserting the newly-fetched (not remembered) state renders.
- 403 on the grants fetch renders `RestrictedState`; any other failure renders `ErrorState` (never a silently-empty permission list, which would look identical to "this role really has no permissions").
- Save button uses `mutation.isPending` (disabled + no duplicate submission verified directly).
- Dirty-state indicator ("You have unsaved changes.") follows the same non-blocking text-hint convention already established on `CompanySettingsPage` — no new blocking-confirm pattern was invented.
- New `ManagePermissionsDialog.test.tsx` (9 tests) exercises the dialog directly via props (`open`/`role`) rather than through the Roles table's row-actions `DropdownMenu` — the same documented Radix+jsdom environment limitation from Phase 12/13 still applies to that menu's *click-to-open* path, but every actual editing behavior (pre-check, isolation, save semantics, persistence-on-reopen, error states, duplicate-submit prevention) is fully covered this way, not skipped.
- Frontend tests: 280 total, 274 passed, **6 skipped — unchanged baseline** (14 new tests: 9 in `ManagePermissionsDialog.test.tsx`, `RolesPage.test.tsx` updated). TypeScript: PASS. Build: PASS.
- Live HTTP verification performed against a genuinely running `manage.py runserver` (not just Django's test client) — full lifecycle (login → list roles → read initial grants → add a grant → confirm persisted → remove a grant → confirm persisted → cross-tenant 404 → unauthenticated 401) all passed; verification data cleaned up afterward.
- Visual QA: **PENDING** — no browser tooling available in this environment.

## Phase 15 — Admin & Settings Completion Audit

| Task | Description | Status |
|---|---|---|
| F38 | Real workspace switcher — Header dropdown backed by a reactive `activeCompanyStore`, wired into the axios client's `companyId` param on every request | Review |
| F39 | Product Categories 403 handling, orphaned Permission catalog page added to Settings nav/command palette, stale role-delete copy corrected | Review |

**Implementation notes (F38/F39):**
- **Workspace switching was a functional bug, not just a missing feature.** `TenantJWTAuthentication` (backend) resolves tenant scope per-request from a `companyId` query param/body field — it was never baked into the JWT — but `apiClient` never attached one anywhere. Confirmed live: any user with more than one active company membership got a bare 403 (`"Multiple active company memberships found; specify companyId."`) on every single non-exempt call. The Header's "· +more workspaces" text was decorative — it never changed backend tenant context, exactly the anti-pattern this task was told not to build.
- Fix: new `frontend/src/lib/activeCompany.ts` (plain module-level pub-sub store, not React state, so the axios request interceptor — which runs outside React — can read it synchronously); `apiClient`'s request interceptor now attaches the stored `companyId` to every outgoing request; `useCurrentCompanyId` made reactive via `useSyncExternalStore` and normalizes to the first membership whenever the stored id is missing or no longer valid (a switched account, a revoked membership); Header's user menu gained a real "Switch workspace" list wired to every active membership.
- **Cache safety on switch**: most existing query keys in this app (clients, projects, products, roles, memberships, ...) were never designed to carry `companyId` — there was only ever one tenant per session until now. Rather than rewrite every module's key factory (out of scope, high blast radius), switching calls `queryClient.clear()` (a deliberate full reset, not a targeted invalidation) and navigates to `/dashboard` so no stale detail page from the old tenant renders. `company.detail(id)`/`role.permissions(id)`-style keys that already embed an id are unaffected either way.
- **Role delete safety root cause found live** (see `BACKEND_TASKS.md` BE-073): soft-deleting a role left it granting full access to every member still assigned to it. Fixed backend-side; the Roles page's delete-confirmation copy and its `Info` footer note (previously "does not automatically reassign") were corrected to describe the real new behavior — members are unassigned (not reassigned), losing the role's permissions immediately.
- Orphaned page found and fixed: `/settings/permissions` (Permission catalog) had a live route but no entry anywhere in `SETTINGS_NAV_GROUPS` — reachable only by typing the URL. Added to the Organization group, which also surfaces it on the Settings landing page and its own sub-nav rail automatically. Command palette gained the 3 settings pages it was missing (Product Categories, Profile, Security).
- Product Categories' 403 path fell through to the generic `ErrorState` (with a misleading "Try again" retry action) instead of `RestrictedState`, inconsistent with every other Settings page — corrected.
- New tests: `activeCompany.test.ts` (3), `useCurrentCompanyId.test.tsx` (4, covering default-to-first-membership, honoring a valid stored selection, falling back when the stored id is stale/revoked, and single-membership `hasMultipleCompanies=false`). Frontend tests: 287 total, 281 passed, **6 skipped — unchanged baseline**. TypeScript: PASS. Build: PASS.
- Live HTTP verification: seeded one user with active memberships in two companies, confirmed no-`companyId` returns the exact 403 the interceptor now avoids, confirmed `?companyId=A`/`?companyId=B` each return correctly tenant-isolated data for the same user, confirmed the role-delete fix end-to-end. All seeded data deleted afterward.
- Visual QA: **PENDING** — no browser tooling available in this environment; the switcher's click-driven interaction (Radix `DropdownMenu`) could not be exercised in Jest either, per the established environment limitation — its underlying logic (store, hook, interceptor) is covered instead, consistent with the `ManagePermissionsDialog` precedent.

## Not Yet Started

Per `06_UI/Wireframes.md`'s module order: Activity Log is blocked (see Phase 10), not merely deferred. Sales/Project reports (no backend endpoint exists). Last-owner/protected-role safety (blocked on `Role.system_key`, BE-069).
