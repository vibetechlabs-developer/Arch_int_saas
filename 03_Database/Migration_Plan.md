# Database Migration Plan

**Status:** Draft — sequencing for MVP (Phase 1–2) scope only, dependency-ordered against `03_Database/Database_Schema.md`. Do not create Phase 3+ tables (Lead, Site Visit, Design, Vendor, Purchase Order, Inventory, Site Daily Log, Snag, Handover, Notification) until that phase is scheduled in `09_Project/Roadmap.md` — they get their own migration numbers (028+) at that time, not pre-created.

**Migration tool note:** with the stack now confirmed as Django/DRF (`02_Architecture/Technical_Architecture.md`), Django generates migrations per-app, each with its own local sequence (`0001_initial.py`, `0002_...`). The numbering below (`001`–`027`) is the **cross-app build/dependency order**, not literal Django filenames — it dictates which Django app must exist and be migrated before the next app's models can declare a `ForeignKey` to it. Within an app, Django's own auto-numbering applies.

---

## Rule

**No table is created before every table it has a foreign key to already exists.** The order below is derived directly from the foreign keys defined in `Database_Schema.md` — it is not arbitrary.

---

## Migration Sequence

| # | Migration | Table(s) | Depends On | Why This Position |
|---|---|---|---|---|
| 001 | `create_plans` | `plan` | — | No FKs; needed before `company` |
| 002 | `create_companies` | `company` | `plan` | `company.plan_id → plan.id` |
| 003 | `create_subscriptions` | `subscription` | `company`, `plan` | Links a company to its plan over time |
| 004 | `create_platform_admins` | `platform_admin` | — | Independent of tenant tables; platform-layer only |
| 005 | `create_users` | `user` | — | Global identity table, no FK yet |
| 006 | `create_roles` | `role` | `company` (nullable) | Default roles are global (`company_id NULL`); custom roles reference `company` |
| 007 | `create_permissions` | `permission` | — | Static reference table |
| 008 | `create_role_permissions` | `role_permission` | `role`, `permission` | Junction table, needs both sides to exist |
| 009 | `create_company_memberships` | `company_membership` | `company`, `user`, `role` | This is where tenant scope + role actually attach to a user (`05_Security/Tenant.md`) |
| 010 | `create_audit_log` | `audit_log` | `company` (nullable), `user` | Must exist before any module that writes audit entries goes live |
| 011 | `create_clients` | `client` | `company` | First tenant-owned business entity |
| 012 | `create_projects` | `project` | `company`, `client`, `user` (assigned_to) | `project.client_id → client.id` |
| 012a | `create_project_members` | `project_member` | `company`, `project`, `user` (member, assigned_by) | **Added 2026-08-27, not in the original 001–027 sequence** — approved deviation, see note below |
| 013 | `create_product_categories` | `product_category` | `company` | |
| 014 | `create_product_subcategories` | `product_subcategory` | `product_category` | |
| 015 | `create_products` | `product` | `product_subcategory` | |
| 016 | `create_boq` | `boq` | `project` | One BOQ per project |
| 017 | `create_boq_sections` | `boq_section` | `boq` | |
| 018 | `create_boq_items` | `boq_item` | `boq_section`, `product` (nullable) | Item may reference a catalog product or be free-text |
| 019 | `create_quotations` | `quotation` | `project`, `boq` (nullable), `client` | Quotation may or may not derive from a BOQ |
| 020 | `create_quotation_items` | `quotation_item` | `quotation`, `product` (nullable) | |
| 021 | `create_contracts` | `contract` | `project`, `quotation` | Generated from an approved quotation |
| 022 | `create_invoices` | `invoice` | `project`, `contract` (nullable), `quotation` (nullable), `client` | Invoice may originate from a contract or directly from an approved quotation |
| 023 | `create_invoice_items` | `invoice_item` | `invoice` | |
| 024 | `create_payments` | `payment` | `invoice`, `client`, `project` | |
| 025 | `create_expenses` | `expense` | `company`, `project`, `user` (added_by, employee) | |
| 026 | `create_tasks` | `task` | `project`, `user` (assigned_to) | |
| 027 | `create_documents` | `document` | `project`, `user` (uploaded_by) | Generic `entity_type`/`entity_id` pattern also allows attaching to other entities later |
| 028 | `create_leads` | `lead` | `company`, `clients` (converted_client, nullable), `projects` (converted_project, nullable), `user` (assigned_to, nullable) | **Phase 3 table, built ahead of schedule 2026-09-15 — see Deviations below.** |

---

## Deviations From This Plan

- **`project_member` (012a), added 2026-08-27, implemented in BE-026 (2026-08-31).** The original 001–027 sequence gave Project only a single `assigned_to` FK — no multi-user "Team" table. `01_Business/FRS.md` §10 and `02_Architecture/Solution_Architecture.md` §3 both name Team as a distinct aggregated concept, and `04_API/Project_API.md` documents `/team` add/remove-by-user endpoints that a single FK cannot represent. Backend Lead approved adding `project_member` (fields: `company`, `project`, `user` nullable, `assigned_by` nullable — see `BACKEND_TASKS.md` BE-026) as a documented exception to this plan rather than silently building it unrecorded. `assigned_to` is unaffected and remains the primary/point-of-contact field. Implemented as `apps/projects/migrations/0002_projectmember.py` (Django's own per-app auto-numbering — this table did not get a real standalone migration numbered "012a"; that label is this plan's cross-app-ordering placeholder only), with a soft-delete-aware `UniqueConstraint(project, user)` preventing duplicate active memberships.

- **`lead` (028), added and implemented 2026-09-15 (BE-061).** This document's own header and `09_Project/Roadmap.md` both gate Phase 3+ tables behind explicit client confirmation/scheduling. This table was built ahead of that gate on the strength of the product owner's own explicit in-session instruction to continue building the remaining SaaS modules beyond Phases 1–2 — a real-time authorization substituting for the normally-required Roadmap scheduling step, not a silent skip of the gate. Flagged here transparently per this project's standing practice of disclosing any such deviation rather than proceeding as if no gate existed. Fields/status vocabulary are a literal transcription of `01_Business/FRS.md §8`'s documented Lead flow (no field list was documented, unlike Client's explicit field set) — see `apps/leads/models.py`'s own docstring for the exact reasoning. Implemented as `apps/leads/migrations/0001_initial.py` (Django's own per-app auto-numbering; "028" above is this plan's cross-app-ordering placeholder only, matching the `012a` precedent).

---

## Dependency Groups (for parallel work planning)

Migrations within the same group have no FK relationship to each other and can be developed/reviewed in parallel by different developers; groups themselves must land in order.

```
Group A (Platform):        001 plans → 002 companies → 003 subscriptions → 004 platform_admins
Group B (Identity/Access):  005 users → 006 roles → 007 permissions → 008 role_permissions → 009 company_memberships → 010 audit_log
Group C (Commercial core):  011 clients → 012 projects
Group D (Catalog):          013 categories → 014 subcategories → 015 products        (can run parallel to Group C after 'company' exists)
Group E (BOQ):              016 boq → 017 boq_section → 018 boq_item                  (needs Group C + Group D)
Group F (Quotation→Contract): 019 quotation → 020 quotation_item → 021 contract        (needs Group E)
Group G (Invoice→Payment):   022 invoice → 023 invoice_item → 024 payment              (needs Group F)
Group H (Cost/Ops):          025 expense, 026 task, 027 document                       (needs Group C only — can start as soon as 'project' exists, does not block on Groups E–G)
```

Note that **Group H (Expense/Task/Document) only depends on `project`**, not on BOQ/Quotation/Invoice — so backend work on Expenses can start in parallel with BOQ/Quotation/Invoice work once Group C lands, even though `09_Project/Module_Dependency_Map.md`'s *feature-completion* order still sequences Expense after the financial modules for product/testing coherence. Migration order (this document) and feature build order (`Module_Dependency_Map.md`) are related but not identical — a table can exist before the feature built on top of it is finished.

## Rollback Policy

- Every migration must have a reversible down-migration (Django migrations are reversible by default when using standard field operations — avoid data-destructive `RunPython` steps without an explicit reverse function).
- Never edit a migration that has already been applied to any shared environment (staging/production) — create a new migration to correct it, per `00_Development_Standards/Git_Strategy.md` §7 (expand/contract pattern).

## Seed Data (post-migration, not part of the schema migrations themselves)

After migration 007 (`permissions`) and 006 (`roles`): seed the fixed default roles (Owner, Admin, Project Manager, Designer/Architect, Accountant, Sales) and their `role_permission` mappings per `05_Security/Permissions.md` §3 — this is application seed data, run once per environment, not a schema-altering migration.
