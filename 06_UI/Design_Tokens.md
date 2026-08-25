# Design Tokens
## Color · Typography · Spacing · Radius · Shadow · Motion · Z-Index · States

**Status:** Draft — Steps 3–8 of the design system build sequence. All values are semantic tokens (never hardcode a raw hex/px value in a component — reference the token). Implemented as Tailwind theme extensions + CSS custom properties (for light/dark swap) once code begins; this document is the source of truth those config files are generated from.

---

## 1. Color System

### 1.1 Palette Philosophy

A restrained neutral foundation (warm-toned charcoal/stone, not cold gray) plus exactly one brand accent and three semantic colors. Color communicates state and meaning — it is never used decoratively (`Design_Principles.md` §3.2).

### 1.2 Neutral Scale (shared base for both themes)

| Token | Hex | Usage |
|---|---|---|
| `neutral-0` | `#FFFFFF` | Pure white — light-mode elevated surfaces only |
| `neutral-25` | `#FAFAF8` | Light-mode app background (warm off-white, not stark white) |
| `neutral-50` | `#F5F4F1` | Light-mode secondary surface / subtle fill |
| `neutral-100` | `#EDEBE6` | Light-mode hover fill |
| `neutral-200` | `#E3E0D9` | Light-mode border (subtle) |
| `neutral-300` | `#D2CEC4` | Light-mode border (strong) / dividers |
| `neutral-500` | `#8C887F` | Tertiary text (both themes, adjusted per theme — see §1.3/1.4) |
| `neutral-600` | `#5F5C56` | Secondary text (light mode) |
| `neutral-800` | `#332F2A` | Elevated dark-mode surface |
| `neutral-900` | `#1C1B19` | Primary text (light mode) / near-black |
| `neutral-950` | `#121114` | Dark-mode app background (not pure `#000`) |

### 1.3 Light Mode Semantic Tokens

| Token | Value | Usage |
|---|---|---|
| `bg-app` | `neutral-25` | App background |
| `bg-surface` | `neutral-0` | Cards, panels, table rows |
| `bg-surface-secondary` | `neutral-50` | Nested/inset surfaces, sidebar |
| `bg-hover` | `neutral-100` | Row/item hover fill |
| `border-subtle` | `neutral-200` | Default borders, dividers |
| `border-strong` | `neutral-300` | Input borders, emphasized dividers |
| `text-primary` | `neutral-900` | Headings, primary content |
| `text-secondary` | `neutral-600` | Supporting text, labels |
| `text-tertiary` | `neutral-500` | Placeholder, disabled, metadata |
| `text-on-accent` | `#FFFFFF` | Text on filled accent surfaces |

### 1.4 Dark Mode Semantic Tokens (independently tuned, not inverted)

| Token | Value | Usage |
|---|---|---|
| `bg-app` | `neutral-950` (`#121114`) | App background |
| `bg-surface` | `#1A191D` | Cards, panels — one step up from app background |
| `bg-surface-secondary` | `#201F24` | Sidebar, nested surfaces |
| `bg-hover` | `#28272C` | Row/item hover fill |
| `border-subtle` | `#2C2B30` | Default borders, dividers |
| `border-strong` | `#38373D` | Input borders |
| `text-primary` | `#F2F1EE` | Headings, primary content — never pure `#FFFFFF` (too harsh against dark bg) |
| `text-secondary` | `#A8A5A0` | Supporting text |
| `text-tertiary` | `#726F6A` | Placeholder, disabled, metadata |
| `text-on-accent` | `#0F0E12` | Text on filled accent surfaces (accent is lightened for dark mode — see §1.5) |

### 1.5 Brand Accent — "Ink Indigo"

A sophisticated, desaturated indigo-violet, distinctive from generic SaaS "electric purple."

| Token | Light Mode | Dark Mode | Usage |
|---|---|---|---|
| `accent-50` | `#EEECFB` | — | Subtle accent fill (selected row, active nav background) |
| `accent-400` | — | `#8C7FE8` | Dark-mode accent (lightened for contrast against dark bg) |
| `accent-500` | `#4A3FA0` | — | Default light-mode accent — primary buttons, links, active states |
| `accent-600` | `#3D3385` | `#7A6DE0` | Hover state |
| `accent-700` | `#2F2868` | — | Pressed state |

### 1.6 Semantic Status Colors

| Status | Light Mode | Dark Mode | Usage |
|---|---|---|---|
| **Success** | `#1F7A5C` (text/icon) / `#E4F5EE` (fill) | `#4ADE9C` / `#0F2B22` | Paid, approved, completed, active |
| **Warning** | `#B7791F` (text/icon) / `#FBF0DA` (fill) | `#E8B04E` / `#2B2210` | Overdue-soon, pending approval, on hold |
| **Destructive** | `#B3261E` (text/icon) / `#FBEAE9` (fill) | `#F2857D` / `#2E1512` | Overdue, cancelled, rejected, delete actions |
| **Info** (neutral-accent, non-brand) | `#3B6EA5` / `#E9F1F8` | `#7FB3E0` / `#12232E` | Informational banners distinct from brand accent |

**Rule:** status colors are used only for their semantic meaning (a status badge, an alert, a validation message) — never as a generic decorative accent on a card or icon that has no status meaning.

### 1.7 AI Surface Accent (reserved for Phase 5, defined now for forward compatibility)

A soft violet-to-amber gradient reserved exclusively for AI-native surfaces (`Application_Shell_Navigation.md` §6, Phase 5 per `09_Project/Roadmap.md`) — `accent-500` → `#C9A15E` at low opacity, used only as a subtle background wash behind AI insight cards, never as a solid fill, and never used outside AI-attributed content (so users learn to recognize "this came from AI" by the visual language alone).

---

## 2. Typography

**Font family:** Inter (primary), with Geist or Plus Jakarta Sans as acceptable substitutes if licensing/availability requires it — pick one and apply project-wide, never mix. Numeric/tabular contexts use Inter's tabular figures (`font-variant-numeric: tabular-nums`) so columns of numbers align.

| Token | Size / Line-Height | Weight | Usage |
|---|---|---|---|
| `text-display` | 40px / 48px | 600 | Marketing/onboarding hero only — rare in-app |
| `text-h1` | 32px / 40px | 600 | Page title |
| `text-h2` | 24px / 32px | 600 | Section heading |
| `text-h3` | 20px / 28px | 600 | Card/panel heading |
| `text-h4` | 16px / 24px | 600 | Sub-section, table group header |
| `text-body` | 14px / 20px | 400 | Default body text, table cells, form values |
| `text-small` | 13px / 18px | 400 | Secondary/supporting text, helper text |
| `text-caption` | 12px / 16px | 500 | Metadata, timestamps |
| `text-label` | 12px / 16px | 600, uppercase, +0.04em tracking | Form labels, table headers, badges |
| `text-kpi` | 28–36px / 1.1 | 600, tabular-nums | Dashboard KPI figures — the one place large bold numbers are correct (`Design_Principles.md` §3.3) |

**Weight discipline:** default body copy is 400. Weight steps up (500/600) only to signal hierarchy (headings, labels, emphasis) — never use 700+ in-app; it reads as shouting against this palette's restraint.

---

## 3. Spacing Scale

4px base unit, used for all padding/margin/gap — no arbitrary pixel values in components.

| Token | Value |
|---|---|
| `space-1` | 4px |
| `space-2` | 8px |
| `space-3` | 12px |
| `space-4` | 16px |
| `space-5` | 20px |
| `space-6` | 24px |
| `space-8` | 32px |
| `space-10` | 40px |
| `space-12` | 48px |
| `space-16` | 64px |
| `space-20` | 80px |
| `space-24` | 96px |

Default component internal padding: `space-4` (16px). Default gap between related fields: `space-3` (12px). Default gap between sections: `space-8`/`space-12`.

---

## 4. Radius Scale

Restrained — most surfaces use `md`; `xl`/`full` are reserved, not defaults.

| Token | Value | Usage |
|---|---|---|
| `radius-none` | 0px | Table cells, dense list rows |
| `radius-sm` | 4px | Badges, small controls |
| `radius-md` | 6px | Buttons, inputs, default control radius |
| `radius-lg` | 8px | Cards, panels |
| `radius-xl` | 12px | Modals, large surfaces |
| `radius-2xl` | 16px | Rare — large marketing/onboarding surfaces only |
| `radius-full` | 9999px | Avatars, pills, status dots |

**Explicit anti-pattern:** do not apply `radius-xl`/`2xl` to ordinary cards — this is the "excessive rounded cards" look called out in `Design_Principles.md` §2 to avoid.

---

## 5. Shadow System

Layered and subtle — never a single heavy drop shadow.

| Token | Value (light mode) | Usage |
|---|---|---|
| `shadow-xs` | `0 1px 2px rgba(28,27,25,0.04)` | Inputs, subtle separation |
| `shadow-sm` | `0 1px 3px rgba(28,27,25,0.06), 0 1px 2px rgba(28,27,25,0.04)` | Cards at rest |
| `shadow-md` | `0 4px 8px rgba(28,27,25,0.06), 0 2px 4px rgba(28,27,25,0.04)` | Dropdowns, popovers |
| `shadow-lg` | `0 12px 24px rgba(28,27,25,0.08), 0 4px 8px rgba(28,27,25,0.04)` | Modals, command palette |
| `shadow-focus` | `0 0 0 3px rgba(74,63,160,0.35)` (accent-500 at 35%) | Focus ring — see §7 |

Dark mode: same structure, black-based shadows read as near-invisible against a dark background — dark-mode elevation is communicated primarily through the surface-color steps in §1.4 (`bg-surface` vs `bg-surface-secondary`), with shadows reduced to ~40% opacity of their light-mode values, used only on true overlays (modal, popover).

---

## 6. Motion Tokens

| Token | Duration | Easing | Usage |
|---|---|---|---|
| `motion-instant` | 0ms | — | State that must feel immediate (checkbox check) |
| `motion-fast` | 140ms | `ease-out` | Button hover/press, small control feedback |
| `motion-standard` | 200ms | `cubic-bezier(0.4, 0, 0.2, 1)` | Dropdown, tab switch, tooltip, most transitions |
| `motion-slow` | 320ms | `cubic-bezier(0.16, 1, 0.3, 1)` | Modal/drawer open-close, route transition |
| `motion-emphasis` | 480–600ms | `cubic-bezier(0.16, 1, 0.3, 1)`, staggered 40–60ms per item | KPI count-up, chart entrance, timeline reveal |

Full rationale and the "why" behind each tier: `Design_Principles.md` §5.

---

## 7. Interactive States

| State | Treatment |
|---|---|
| **Hover** | `bg-hover` fill (interactive rows/items) or `-1px` translateY + `shadow-sm→shadow-md` (buttons/cards where elevation makes sense) — `motion-fast` |
| **Focus** | `shadow-focus` ring, 2px offset from element edge, always visible (never `outline: none` without an explicit replacement) — see `Responsive_Accessibility.md` §2 |
| **Active/Pressed** | Scale to 98% + fill darkens one step (`accent-600`) — `motion-instant`→`motion-fast` |
| **Disabled** | 40% opacity, `cursor: not-allowed`, no hover/focus treatment, `pointer-events: none` on the interactive element itself but the wrapping element remains reachable for a tooltip explaining why (see `Component_Inventory.md` §Tooltip) |
| **Loading** | Skeleton (`Component_Inventory.md` §Skeleton) for content; spinner + disabled state for in-flight actions on buttons |
| **Error** | `border-destructive` + `text-destructive` helper text below the field, per `00_Development_Standards/Validation_Standards.md` §7 |
| **Empty** | See `Component_Inventory.md` §EmptyState — never a bare "No data" string |

---

## 8. Z-Index Scale

| Token | Value | Usage |
|---|---|---|
| `z-base` | 0 | Default document flow |
| `z-dropdown` | 1000 | Select/combobox menus |
| `z-sticky` | 1100 | Sticky table headers, sticky page headers |
| `z-overlay` | 1200 | Drawer/modal backdrop |
| `z-modal` | 1300 | Dialog/drawer content |
| `z-popover` | 1400 | Popovers above modals (e.g. a select inside a dialog) |
| `z-toast` | 1500 | Toast notifications |
| `z-tooltip` | 1600 | Tooltips — always above everything else |

---

## 9. Breakpoints

See `Responsive_Accessibility.md` §1 for the full responsive strategy; the raw values:

| Token | Min-width |
|---|---|
| `xs` | 375px |
| `sm` | 430px |
| `md` | 768px |
| `lg` | 1024px |
| `xl` | 1280px |
| `2xl` | 1440px |
