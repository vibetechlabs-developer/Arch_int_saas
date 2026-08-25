# Project API (Draft)
## INT Projects — Multi-Company Interior & Architecture Management SaaS

**Status:** Draft endpoint sketch.

---

## Scope

Project as the central operational entity, plus its directly-owned sub-resources that don't have their own dedicated API doc (Tasks, Documents, Team). BOQ/Quotation/Invoice/Payment/Expense have their own docs (`BOQ_API.md`, `Finance_API.md`) but are always accessed nested under a project.

## Project Endpoints

| Method | Path | Purpose | Permission |
|---|---|---|---|
| GET | `/companies/{companyId}/projects` | List projects (filter: status, client, assigned user, priority, date range) | `project.view` |
| POST | `/companies/{companyId}/projects` | Create project | `project.create` |
| GET | `/companies/{companyId}/projects/{projectId}` | Project overview (client, team, status, timeline, cost summary) | `project.view` |
| PATCH | `/companies/{companyId}/projects/{projectId}` | Edit project (name, dates, priority, assigned user) | `project.edit` |
| PATCH | `/companies/{companyId}/projects/{projectId}/status` | Transition project status (Draft→Planning→...→Completed, or On Hold/Cancelled) | `project.edit` |
| DELETE | `/companies/{companyId}/projects/{projectId}` | Soft-delete project | `project.delete` |
| GET | `/companies/{companyId}/projects/{projectId}/cost-summary` | Revenue − Cost = Profit breakdown (materials/labour/vendor/other) | `project.view`, `financial.view` |

## Team

| Method | Path | Purpose |
|---|---|---|
| GET | `/companies/{companyId}/projects/{projectId}/team` | List assigned team members |
| POST | `/companies/{companyId}/projects/{projectId}/team` | Assign a user to the project |
| DELETE | `/companies/{companyId}/projects/{projectId}/team/{userId}` | Remove from project team |

## Tasks

| Method | Path | Purpose |
|---|---|---|
| GET | `/companies/{companyId}/projects/{projectId}/tasks` | List tasks |
| POST | `/companies/{companyId}/projects/{projectId}/tasks` | Create task (title, assignee, due date) |
| PATCH | `/companies/{companyId}/projects/{projectId}/tasks/{taskId}` | Update/complete task |

## Documents

| Method | Path | Purpose |
|---|---|---|
| GET | `/companies/{companyId}/projects/{projectId}/documents` | List documents |
| POST | `/companies/{companyId}/projects/{projectId}/documents` | Upload document (stored in object storage, tagged company+project+version) |
| GET | `/companies/{companyId}/projects/{projectId}/documents/{documentId}/download` | Download (signed URL) |

## Notes

- Status transitions should be validated server-side against the allowed lifecycle graph (`Draft → Planning → Design → Quotation → Approved → Execution → Quality Check → Handover → Completed`, plus side-transitions to `On Hold`/`Cancelled`) — not freely settable to any value.
- `cost-summary` must be computed live from Expense + Invoice/Payment records, never cached as a separately-maintained field, per the "reports derived from transactional data" principle in `02_Architecture/Solution_Architecture.md`.
- Design, Site Activity, Snags, and Contract endpoints belong here conceptually but are Phase 3–4 — to be added once those modules are scheduled (see `09_Project/Roadmap.md`).
