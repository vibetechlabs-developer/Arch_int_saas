# Risk Register (Draft)
## INT Projects — Multi-Company Interior & Architecture Management SaaS

**Status:** Draft — risks identified from the nature of the requirements themselves; likelihood/impact scoring and mitigation owners to be assigned by the project team.

---

| # | Risk | Why It Matters Here | Proposed Mitigation |
|---|---|---|---|
| 1 | Cross-tenant data leakage | Explicit hard requirement from the client ("Company A must never access Company B's data") — a single bug here is a trust-ending failure, not a normal bug | Defense-in-depth per `05_Security/Tenant.md` (middleware + query layer + optional Postgres RLS); mandatory isolation tests as a CI gate |
| 2 | Building screens before requirements approval | Source doc explicitly warns against this (§36 "What Should NOT Be Done Yet") | Enforce the Phase 0 Requirement Approval Gate in `09_Project/Roadmap.md` before Phase 1 build starts |
| 3 | Treating modules as independent CRUD screens instead of a connected workflow | Source doc explicitly calls this out as the current system's weakness (§40 Architect's Conclusion) | Design review checkpoint at end of Phase 2 against the target flow in `02_Architecture/Solution_Architecture.md` §5 |
| 4 | Scope creep from Phase 3–5 features pulled into MVP | Large future surface (CRM, Design, Procurement, Site Mgmt, Client Portal) could balloon Phase 1–2 timeline if not held firm | Roadmap phase boundaries in `09_Project/Roadmap.md`; any pull-forward requires explicit client sign-off |
| 5 | Financial calculation errors (BOQ/Quotation/Invoice totals, profit/margin) | These numbers are the core value proposition ("replace spreadsheets") — errors undermine the whole product's credibility | Server-side computation only (never trust client-submitted totals); dedicated test coverage per `08_QA/Test_Cases.md` §6–10 |
| 6 | Undefined multi-tenancy strategy at schema level | Shared-schema vs. schema-per-tenant vs. DB-per-tenant has major cost/complexity implications discovered late is expensive to reverse | Decide and document in `02_Architecture/Technical_Architecture.md` §3 before Phase 1 schema work begins |
| 7 | Audit log treated as an afterthought | Required for invoices/payments/expenses/quotations/permissions/project changes — retrofitting audit logging onto existing tables later is disruptive | Build the audit log write path in Sprint 1 (see `09_Project/Sprint_Planning.md`), not deferred to later phases |
| 8 | Role/permission model finalized too late | Nearly every module's API and UI depends on the permission model; if it changes after Phase 2 build starts, significant rework follows | Confirm `05_Security/Permissions.md` open items (canonical permission code list, custom role support) during Phase 0 |
| 9 | Client portal isolation requirements underestimated | Client role must never see other clients, internal expenses, salaries, notes, or margins — a stricter isolation boundary than internal roles | Treat as its own security model, not a reuse of internal RBAC (`05_Security/Permissions.md` §6), designed before Phase 5 starts, not bolted on |
| 10 | Currency/numbering/tax rules not yet confirmed per company | Affects invoice/quotation numbering, GST handling, and multi-currency support — unresolved in the source document | Raise as an open question with the client (see `01_Business/PRD.md` §8) before finalizing `03_Database/Database_Schema.md` |

## Review Cadence

This register should be reviewed at the end of each phase in `09_Project/Roadmap.md`, with new risks added as the technical architecture decisions in `02_Architecture/Technical_Architecture.md` §8 are resolved.
