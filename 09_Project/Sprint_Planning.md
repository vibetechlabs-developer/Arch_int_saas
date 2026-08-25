# Sprint Planning

**Status:** Not started — blocked on team composition, velocity, and sprint length, none of which are defined in the source requirements.

## Prerequisites

1. `09_Project/Roadmap.md` phases confirmed with client
2. Team size/roles assigned (backend, frontend, QA)
3. Sprint cadence decided (e.g. 1-week vs. 2-week sprints)
4. `02_Architecture/Technical_Architecture.md` §8 Open Decisions resolved, since sprint 1 work depends on the chosen stack

## Suggested First-Sprint Candidates (once unblocked)

Drawn from Phase 1 — Foundation (`09_Project/Roadmap.md`), roughly in dependency order:
1. Multi-tenant data model + `company`/`user`/`company_membership`/`role`/`permission` tables
2. Authentication (login, session/token issuance)
3. Tenant/Permission middleware (the mandatory request flow in `05_Security/Tenant.md` §2)
4. Company creation + user invitation flow
5. Audit log write path

Detailed sprint-by-sprint backlog to be created once the prerequisites above are resolved.
