# Responsive & Accessibility Strategy

**Status:** Draft — Steps 12–13 of the design system build sequence.

---

## 1. Responsive Strategy

### 1.1 Target Breakpoints

Per `Design_Tokens.md` §9: `375px`, `430px`, `768px`, `1024px`, `1280px`, `1440px+`. Desktop (`lg`/`1024px` and above) gets full information density; below that, layouts are **intentionally redesigned**, not shrunk.

### 1.2 Layout Adaptation Rules

| Breakpoint | Shell | Tables | Cards/Grids | Forms |
|---|---|---|---|---|
| `2xl`/`xl` (1280–1440px+) | Sidebar expanded by default | Full `DataTable` with all columns | Multi-column grid (project cards, KPI strip) | Multi-column sections |
| `lg` (1024px) | Sidebar collapsible, defaults to collapsed on first visit at this width | Full table, secondary columns may hide behind a "more columns" toggle | 2-column grid | Multi-column sections, narrower |
| `md` (768px, tablet) | Sidebar becomes an overlay drawer (not permanently docked) | Table switches to **priority columns** (2–3 most important fields visible, rest behind a row-expand) or horizontal scroll for genuinely tabular data (e.g. BOQ line items) — decided per-table based on which columns are truly essential | Single column | Single column, sections stack |
| `sm`/`xs` (375–430px, mobile) | Sidebar is a full-screen drawer; header collapses to essential actions + a menu trigger | Table becomes a **stacked card list** (one record per card, key fields only, tap to open detail) — never a shrunk table with horizontal scroll as the only mobile experience for primary list views | Single column, full-width cards | Single column, one field group visible at a time for very long forms where appropriate |

**Rule from `Design_Principles.md` §3.4 (data-dense, not cluttered) applied here:** density is a desktop feature. Mobile prioritizes the 2–3 fields a user actually needs on a small screen (e.g. client list on mobile: name, outstanding balance, status — not all 10 desktop columns squeezed in).

### 1.3 Mobile-Specific Patterns

- Bottom navigation/action bar used only where it measurably improves reachability for the most common mobile actions (per `01_Business/FRS.md`'s role-driven priorities: add lead, add client, create task, view project, view invoice, update task, notifications) — not a blanket replacement for the sidebar drawer.
- Touch targets minimum 44×44px (exceeds the 32–40px desktop button heights in `Component_Inventory.md` §1 — mobile variants scale up).
- Modals become full-screen sheets on mobile rather than centered dialogs with wasted surrounding space.

### 1.4 Testing Requirement

Every screen is verified at all seven target widths (`375, 390, 430, 768, 1024, 1280, 1440`) before being marked complete, per the quality bar in `Design_Principles.md` §6.

---

## 2. Accessibility Strategy

Accessibility is a **production requirement**, not a polish pass — evaluated on the same quality bar as visual design (`Design_Principles.md` §6).

### 2.1 Keyboard Navigation

- Every interactive element reachable and operable via keyboard alone (`Tab`/`Shift+Tab` to move, `Enter`/`Space` to activate, `Esc` to dismiss overlays).
- Logical tab order follows visual/reading order — never a DOM order that jumps unpredictably.
- `DataTable` (`Component_Inventory.md` §3) supports keyboard row navigation and selection, not just mouse.
- Command Palette (`Application_Shell_Navigation.md` §5) is fully keyboard-operable by design — it's the reference implementation for this principle.

### 2.2 Focus States

Every focusable element shows the `shadow-focus` ring (`Design_Tokens.md` §5, §7) — never `outline: none` without a replacement. Focus is visibly trapped within an open Dialog/Drawer (`Component_Inventory.md` §5) and returns to the triggering element on close.

### 2.3 Semantic HTML & ARIA

- Use native semantic elements (`<button>`, `<nav>`, `<table>`, `<label>`) before reaching for ARIA — ARIA supplements, it doesn't replace, correct markup.
- Icon-only buttons (`Component_Inventory.md` §6) always carry `aria-label`.
- Dialogs/Drawers use `role="dialog"` + `aria-modal="true"` + a labeled title (`aria-labelledby`).
- Dropdowns/Comboboxes expose `aria-expanded`/`aria-activedescendant` per the standard combobox pattern.
- Status badges (`Component_Inventory.md` §7) that convey meaning through color alone also carry a text label — never color-only status communication (relevant for color-blind users, ties to §2.4).

### 2.4 Contrast

All text/background pairs in `Design_Tokens.md` §1.3/§1.4 meet WCAG AA (4.5:1 for body text, 3:1 for large text/UI components) in both light and dark mode. `text-tertiary` is the minimum-contrast tier and is reserved for genuinely secondary metadata, never for anything a user must read to complete a task.

### 2.5 Reduced Motion

`prefers-reduced-motion: reduce` is respected globally:
- Decorative/emphasis-tier animations (`motion-emphasis` reveals, staggered lists, chart entrances) are disabled entirely.
- Functional transitions (modal open/close, route change) shorten to near-instant (`motion-fast` duration, opacity-only, no translate/scale) rather than removed outright — the user still needs to perceive that a state changed.
- No animation, regardless of motion preference, is ever required to understand or operate the interface — motion is always supplementary to a state that's also communicated statically (a checkmark appearing, not just a bounce with no persistent indicator).

### 2.6 Tooltips for Unfamiliar Icons

Any icon-only action whose meaning isn't self-evident from context gets a tooltip on hover/focus (not just hover — keyboard-focus must also trigger it), per `Component_Inventory.md` §6's "prefer text over icon" guidance as the first line of defense.

### 2.7 Screen Reader Considerations

- Live regions (`aria-live="polite"`) for asynchronous status updates that matter but shouldn't interrupt (e.g. "Invoice sent" toast content, save confirmations).
- Table data (`DataTable`) uses proper `<th scope="col">` headers so screen readers can announce column context per cell.
- Empty/error/loading states (`Component_Inventory.md` §12) are announced, not just visually swapped in — a skeleton-to-content transition or an error banner appearing must be perceivable non-visually too.

### 2.8 Never Trade Accessibility for Effect

Per `Design_Principles.md` and this document's framing as a production requirement: if a proposed visual effect (e.g. a blur/glass surface, a low-contrast decorative element) cannot be made to meet the standards above, the effect is adjusted or dropped — not the accessibility requirement.
