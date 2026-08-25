# Component Inventory

**Status:** Draft — Step 9 of the design system build sequence. Every screen in this product composes from the components below; a new visual pattern is added here (and reviewed against `Design_Principles.md`) before it is used on any page. Built on shadcn/ui primitives (`02_Architecture/Technical_Architecture.md` §2) styled to the tokens in `Design_Tokens.md` — shadcn is the primitive layer, not the visual identity; every component below is re-themed, not used with default shadcn styling.

---

## 1. Button

| Variant | Usage |
|---|---|
| `primary` | The one primary action per view (filled `accent-500`, `text-on-accent`) |
| `secondary` | Default supporting action (`bg-surface-secondary`, `border-subtle`, `text-primary`) |
| `outline` | Lower-emphasis action alongside a primary |
| `ghost` | Lowest emphasis — toolbar icon actions, table row actions |
| `destructive` | Delete/cancel/void actions only (`Design_Tokens.md` §1.6 destructive color) — never used for a merely "different" action |
| `link` | Inline text-styled action |

Sizes: `sm` (32px height), `md` (36px, default), `lg` (40px). Icon-only buttons are square at the same height, always paired with an accessible label (`Responsive_Accessibility.md` §2).

States per `Design_Tokens.md` §7. A button performing an async action shows a spinner in place of its label (not alongside) and disables itself for the duration — never allow a double-submit on a financial action (ties to `00_Development_Standards/Error_Handling.md` §6 idempotency).

## 2. Forms & Inputs

Components: `Input`, `Textarea`, `Select`, `Combobox`, `DatePicker`, `Checkbox`, `Radio`, `Switch`, `FileUpload`.

- Label (`text-label` token) always above the field, never placeholder-as-label.
- Required fields marked with a subtle asterisk or "(required)" caption — not color alone (accessibility).
- Helper text (`text-small`, `text-secondary`) below the field for guidance; replaced by error text (`text-small`, `text-destructive`) on validation failure, per `00_Development_Standards/Validation_Standards.md` §7.
- Long forms use named sections (e.g. "Basic Information," "Contact Information," "Billing Information") with generous `space-8` between sections, not one undifferentiated block.
- Inline validation fires on blur, not on every keystroke (avoid error-flashing while the user is still typing).
- Forms with meaningful in-progress state (e.g. a long client/project edit) warn on navigation-away with unsaved changes; autosave is used only where the module's spec calls for a draft state (e.g. Quotation/Expense drafts — `01_Business/FRS.md` §13, §17).

## 3. Table / DataTable

The most heavily used component in the product (`Design_Principles.md` §3.4 — enterprise data density).

**`DataTable` features (reusable across every list screen):**
- Sort (single-column, click header)
- Filter (per-column + a combined filter bar)
- Search (debounced, scoped to the current view)
- Pagination (page-based, per `00_Development_Standards/API_Response_Format.md` §1)
- Column visibility toggle
- Row selection + bulk actions (bulk export, bulk status change where permitted)
- Density control (comfortable/compact)
- Sticky header on scroll
- Saved views (persisted filter+sort+column combinations)

**Visual rules:** minimal borders — row separation via a hairline `border-subtle` or alternating `bg-hover`-tint on hover only, never both; no vertical column borders by default (adds visual noise at high density); row hover uses `motion-fast`; a row that's a link to a detail page uses the whole row as the click target, not just a small icon.

**Table → responsive card fallback:** see `Responsive_Accessibility.md` §1.

## 4. Card

Used for: dashboard KPI tiles, project cards (grid view), summary panels. `bg-surface`, `radius-lg`, `shadow-sm` at rest. A card that is itself a navigation target gets a hover treatment (`shadow-sm → shadow-md`, `motion-fast`); a purely informational card (e.g. a KPI tile) does not — hover elevation implies interactivity and must not be applied where nothing happens on click.

**KPI Card specifically:** label (`text-label`), value (`text-kpi`, tabular-nums), a comparison/trend indicator (small arrow + percentage in success/destructive color depending on direction), and an optional inline sparkline. No large colorful icon tile — see `Design_Principles.md` §2.

## 5. Modal / Dialog / Drawer

- **Dialog:** centered, `radius-xl`, `shadow-lg`, backdrop at low-opacity blur (`Design_Tokens.md` §6 `motion-slow` fade+scale-in from 98%→100%). Used for focused single-task interactions (confirmations, small forms).
- **Drawer:** slides in from the right, full-height, used for larger contextual forms/detail (e.g. quick-view of a record) without leaving the current page context.
- **Confirmation Dialog** (destructive actions specifically): title states the action plainly ("Delete client?"), body states the consequence plainly ("This will permanently remove the client and associated records."), and only the destructive button uses the destructive color — the cancel button is a neutral `outline`/`secondary` button, never styled to compete. Never use the browser's native `confirm()`.

## 6. Icons

Lucide only, project-wide — no mixing icon libraries, no emoji-as-icon (`00_Development_Standards/Naming_Conventions.md`, `02_Architecture/Technical_Architecture.md` §2). Sizes: 16px for inline/table-row icons, 20px for standalone UI icons (buttons, nav), 24px for prominent empty-state/illustration-adjacent use. Icon-only interactive elements always carry an accessible label (`aria-label` or equivalent) — see `Responsive_Accessibility.md` §2. Prefer text over an icon whenever the icon's meaning isn't immediately obvious without a tooltip.

## 7. Badge / Status Pill

Used for entity statuses (Invoice: Draft/Sent/Paid/Overdue..., Project: Planning/Execution/Completed..., Expense: Draft/Submitted/Approved/Paid). `radius-full` or `radius-sm`, semantic color per `Design_Tokens.md` §1.6 fill+text pairing, `text-caption` weight. One status per badge — never stack multiple badges to convey compound state; use a single badge with the current authoritative status.

## 8. Avatar

Circular (`radius-full`), used for user/team display. Fallback: initials on a deterministic neutral-tone background (derived from the user's name/id, not random) when no image is set. Grouped avatars (project team) overlap slightly with a `bg-surface` ring separator, capped with a "+N" overflow indicator beyond 4–5 shown.

## 9. Toast

Bottom-right (desktop) / bottom-center (mobile), `motion-standard` slide+fade in, auto-dismiss with a subtle progress indicator for timed messages, manually dismissible. Used for: confirmation of a completed action (e.g. "Invoice sent"), not for validation errors (those live inline on the form per §2) or critical errors (those use `Alert`/full error states per `Component_Inventory.md` §12 and `08_QA/Test_Cases.md` error categories).

## 10. Tabs

Underline-indicator style (not boxed/pill tabs) for the primary content-switching pattern on detail pages (Client/Project detail — `04_API/CRM_API.md`, `04_API/Project_API.md`). Active indicator animates its position with `motion-standard`, not an instant jump.

## 11. Command Palette

`Ctrl/Cmd+K` global trigger. Full specification in `Application_Shell_Navigation.md` §5 (this entry exists here for the component list — behavior is documented there, not duplicated).

## 12. Alert / Error / EmptyState / Skeleton

- **Alert:** page/section-level banner for a persistent condition (e.g. "This company's trial ends in 3 days"), semantic color per severity, dismissible only when the underlying condition allows it.
- **Error State** (full-page or section-level, for API/network/permission/404/500 failures): states what happened, why (if knowable), and the next action — never a bare "Error" — per `00_Development_Standards/Error_Handling.md` §4 and §7 and `08_QA/Test_Cases.md`'s error categories. Includes the `requestId` (from `API_Response_Format.md` §4) in a copyable, de-emphasized caption for support reference.
- **EmptyState:** icon (24px, `text-tertiary`) + short headline + one-sentence explanation + a single primary CTA where applicable ("No projects yet" / "Create your first project to start tracking work." / `[Create Project]`). No generic sad-face illustrations — the icon comes from the same Lucide set as the rest of the product.
- **Skeleton:** matches the actual layout of the content it's replacing (skeleton table rows for a table, skeleton KPI tiles for the dashboard strip) — never a generic centered spinner for a screen that has a known layout. See `Responsive_Accessibility.md` for reduced-motion behavior on skeleton shimmer.

## 13. Stat / Sparkline / Chart

- **Stat:** the KPI Card's internal number display (§4) — reusable standalone for inline metrics (e.g. inside a client's financial summary).
- **Sparkline:** minimal inline trend line, no axes/labels, used only alongside a Stat, never as a standalone chart.
- **Chart** (line/bar/donut): full-size charts on `08_QA`/Reports screens only, with legends, axis labels, and tooltips on hover. Donut charts used only for true part-to-whole compositions (e.g. expense category breakdown), never as a default chart type. Entrance uses `motion-emphasis` (`Design_Tokens.md` §6) once, on first viewport entry — not on every re-render.

## 14. Timeline

Vertical, connected-line style with small icons per entry (`Design_Principles.md`-aligned restraint — no large colorful icon bubbles). New entries added to a live timeline animate in with `motion-standard`, not `motion-emphasis` (an activity feed updates too often for a slow reveal to stay pleasant).

## 15. Kanban

Column-based (`Backlog → To Do → In Progress → Review → Completed`), drag-and-drop cards showing priority, assignee avatar, due date, and comment/attachment counts. Drag feedback: card lifts (`shadow-md`), other cards reflow with `motion-fast`, drop settles with a slight spring-like ease (`motion-standard` curve) — no exaggerated physics/bounce.

## 16. Notification Drawer

Right-side drawer (§Modal/Drawer), grouped by category (Mentions/Tasks/Payments/Projects/Quotations/System per `01_Business/FRS.md` §26), unread items marked with a subtle dot indicator (not a loud badge color unrelated to semantic meaning), with a "Mark all as read" action.

## 17. Full Component List (reference)

Button · Input · Select · Combobox · DatePicker · Checkbox · Radio · Switch · FileUpload · Dialog · Drawer · Dropdown · Tooltip · Tabs · Badge · Avatar · Card · Table · DataTable · Pagination · Breadcrumb · Toast · Alert · EmptyState · Skeleton · CommandPalette · Stat · Sparkline · Chart · Timeline · Kanban · NotificationDrawer · ConfirmationDialog

Every page in `Wireframes.md`'s screen inventory is built exclusively from this list — a page needing something not here means the inventory gets extended first, documented here, then used.
