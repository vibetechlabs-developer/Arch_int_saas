# UI Guidelines — Index

**Status:** Draft. This is the entry point into the design system — read this first, then follow the links below in order. This replaces the earlier placeholder now that the full system is drafted.

---

## Design System Documents

| Doc | Covers |
|---|---|
| `Design_Principles.md` | Visual direction ("Architectural Intelligence"), what to avoid, animation philosophy, quality bar |
| `Design_Tokens.md` | Color (light/dark), typography, spacing, radius, shadow, motion, states, z-index, breakpoints |
| `Component_Inventory.md` | Every reusable component (Button, Forms, Table, Card, Modal, Icons, and the full list) |
| `Application_Shell_Navigation.md` | Sidebar, header, command palette, full navigation IA, role-based nav, workspace switcher |
| `Responsive_Accessibility.md` | Breakpoint strategy + layout adaptation rules, full accessibility requirements |
| `Wireframes.md` | Screen inventory, per-screen content briefs, and the module-by-module build sequence |

## Non-Negotiable Guardrails

1. **One design system, zero one-off components.** Every screen is composed from `Component_Inventory.md`. A new visual pattern is added to the inventory (and checked against `Design_Principles.md`) before it appears on a page.
2. **Lucide icons only** — no mixing icon libraries, no emoji-as-icon (`00_Development_Standards/Naming_Conventions.md`, `02_Architecture/Technical_Architecture.md` §2).
3. **Tokens, not hardcoded values.** No raw hex color, arbitrary pixel spacing, or ad hoc shadow/radius value in any component — everything traces back to `Design_Tokens.md`.
4. **Dark mode is mandatory from the start** for every screen, tuned per `Design_Tokens.md` §1.4 — not retrofitted later.
5. **Permission-aware UI, server-enforced authority.** The UI hides what a role can't do (`Application_Shell_Navigation.md` §9); the API remains the actual enforcement boundary (`05_Security/Permissions.md` §5, `05_Security/Tenant.md`).
6. **Build in sequence.** Follow `Wireframes.md`'s Build Sequence — design system → shell → module-by-module, each step approved before the next starts. Never generate every screen at once.
7. **The final result must connect to real APIs.** Every component is structured to consume the `04_API/` contracts and the `API_Response_Format.md` envelope — no fake data shapes that would need rework to connect to the Django/DRF backend (`02_Architecture/Technical_Architecture.md` §2).
8. **Quality bar applies to every screen**, no exceptions — see `Design_Principles.md` §6 (visual, UX, enterprise-readiness, responsive, accessibility).

## Technology Assumptions

Frontend: React + TypeScript + Vite, Tailwind CSS, shadcn/ui as the component primitive layer, Lucide icons, Motion/Framer Motion for animation — confirmed in `02_Architecture/Technical_Architecture.md` §2. shadcn is the primitive layer only; every component in `Component_Inventory.md` is re-themed to this system's tokens, not left in default shadcn styling.

## What "Premium" Means Here

Per `Design_Principles.md` §1: restrained neutral palette, typography-driven hierarchy, purposeful motion, real dark mode — not gradients, glassmorphism, neon accents, or animation for its own sake. The target reaction is *"this is a serious professional business operating system,"* not *"this is another Bootstrap admin panel."*
