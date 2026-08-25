# Design Principles & Direction
## "Architectural Intelligence" — Visual Identity for INT Projects

**Status:** Draft — Step 1–2 of the design system build sequence (`06_UI/UI_Guidelines.md` §Build Sequence). This document defines *why* every token and component decision downstream (`Design_Tokens.md`, `Component_Inventory.md`, `Application_Shell_Navigation.md`) looks the way it does.

---

## 1. Product Design Direction

The name for this visual language is **"Architectural Intelligence"** — the fusion of:

- Modern enterprise SaaS precision (Linear, Stripe, Vercel-grade restraint)
- Architecture/interior-design aesthetic sensibility (the client's own industry — the tool should look like something an architecture firm would be proud to have built)
- Financial-product clarity (numbers are legible, trustworthy, never decorative)
- Editorial typography (hierarchy carries meaning, not just size)
- Subtle depth and sophisticated, restrained motion

**Target reaction on first screen:** *"This is a serious professional business operating system."*
**Explicitly not:** *"This is another Bootstrap admin panel."*

## 2. What We Are Not Building

Reject on sight, in every review:

- Generic purple/blue gradient dashboards
- Excessive rounded corners on every surface
- Glassmorphism as a default, not an exception
- Neon or saturated accent colors
- Oversized colorful icon tiles on KPI cards
- Animation for its own sake (bounce, spin, particle effects)
- A reports page that is a wall of charts with no narrative
- Any component invented ad hoc instead of pulled from `Component_Inventory.md`

## 3. Design Principles

1. **Premium without flashy.** Depth, spacing, and typography carry the "expensive" feeling — not color saturation or heavy shadows.
2. **Color communicates meaning, not decoration.** A neutral foundation (charcoal/warm-off-white/stone) plus one brand accent and three semantic colors (success/warning/destructive). No competing hues.
3. **Typography is the primary hierarchy tool.** Size and weight changes do the work that color and boxes do in lesser dashboards.
4. **Data-dense, not cluttered.** This is an enterprise tool handling real financial data at scale — tables and numbers must stay legible under real data volume, not just in a 5-row demo.
5. **Every animation is purposeful.** See §5 — restraint is the feature.
6. **One design system, zero one-off components.** Every screen composes from `Component_Inventory.md`; a new visual pattern is added to the system before it's added to a page.
7. **Permission-aware by default.** The UI reflects what a role can do (`05_Security/Permissions.md`) — hidden, not just disabled-and-confusing, for actions a role can never perform.
8. **Dark mode is a real second theme**, tuned independently — not an inverted light theme (`Design_Tokens.md` §2).

## 4. Inspiration Without Imitation

Draw restraint from **Linear**, data clarity from **Stripe**, typographic confidence from **Vercel**, modern CRM information density from **Attio**, and structural flexibility from **Notion** — but the result must be an original identity distinctive to this product's own industry (architecture/interior design) and its own accent palette (`Design_Tokens.md` §1). Do not reproduce any of these products' specific layouts, component shapes, or color values.

## 5. Animation Philosophy

> **"I notice the product feels premium, but I don't notice why."**

"Animation-rich" does not mean everything moves. It means every state change that *should* be perceptible is smooth, and everything else is instant.

| Tier | Duration | Use |
|---|---|---|
| Micro-interaction | 120–180ms | Button press, hover, checkbox toggle |
| Standard transition | 200–250ms | Dropdown, tab switch, tooltip |
| Modal/drawer/page | 250–400ms | Dialog open/close, route transition |
| Data/chart reveal | 400–700ms | KPI number count-up, chart entrance, staggered list reveal — used sparingly, only for groups where the reveal itself communicates something (e.g. "these five numbers just loaded together") |

Rules:
- Route transitions: opacity + 4–8px translate only. No full-screen wipes, no dramatic scale.
- Never animate more than one property change per element beyond opacity+transform.
- Staggered reveals only for meaningful groups (a KPI strip, a timeline) — never stagger an entire page's content on every load.
- `prefers-reduced-motion` always respected — see `Responsive_Accessibility.md` §4.

Full token values (durations, easing curves) are defined in `Design_Tokens.md` §5.

## 6. Design Quality Bar

Before any screen is considered finished, it must pass:

**Visual:** Is hierarchy obvious at a glance? Is spacing from `Design_Tokens.md` §3 used consistently? Does it look premium, not template-generated?

**UX:** Can a new user understand the page's purpose within seconds? Is the primary action unambiguous? Are empty/error states (`Component_Inventory.md` §EmptyState/§Alert) actually useful, not generic?

**Enterprise-readiness:** Does it hold up with hundreds/thousands of rows, not just 5 demo rows? Are permissions reflected in what's shown, not just what's clickable?

**Responsive:** Does it work intentionally (not just "shrunk") at every breakpoint in `Responsive_Accessibility.md` §1?

**Accessibility:** Keyboard-navigable, visible focus states, sufficient contrast, screen-reader labeled — see `Responsive_Accessibility.md` §2–3.

If any answer is no, iterate before moving to the next screen — per the build sequence in `06_UI/UI_Guidelines.md`.
