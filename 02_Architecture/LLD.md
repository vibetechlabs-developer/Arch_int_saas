# Low-Level Design (LLD)
## INT Projects — Multi-Company Interior & Architecture Management SaaS

**Status:** Not started — blocked on prerequisites below

---

## Purpose

Detailed, implementation-level design (module internals, class/service boundaries, sequence diagrams, request/response contracts) for each business module.

## Prerequisites Before This Can Be Written

1. `03_Database/Database_Schema.md` — finalized table/column definitions
2. `04_API/` — endpoint contracts per module (Authentication, CRM, Project, BOQ, Finance, ...)
3. `02_Architecture/Technical_Architecture.md` §8 Open Decisions resolved (backend framework, multi-tenancy strategy, hosting)
4. Client sign-off on the Requirement Approval Gate (see `01_Business/BRS.md` §9)

## Planned Contents (once unblocked)

- Per-module service/class design (Company, User/Role, Client, Project, Product/BOQ, Quotation, Contract, Invoice, Payment, Expense, Report)
- Sequence diagrams for key flows (Quotation approval, Invoice→Payment, Tenant-scoped request resolution)
- Error handling and validation rules per endpoint
- Transaction boundaries (e.g., invoice generation from an approved quotation)

Do not begin this document until the prerequisites above are checked off — see `02_Architecture/Solution_Architecture.md` and the source requirements document's "What Should NOT Be Done Yet" section.
