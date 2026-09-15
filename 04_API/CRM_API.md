# CRM API (Draft)
## INT Projects — Multi-Company Interior & Architecture Management SaaS

**Status:** Draft endpoint sketch. `Site Visit` endpoints remain Phase 3 (not MVP, not built) — included here for completeness since they belong to the CRM module conceptually. **`Lead` endpoints were implemented 2026-09-15 (BE-061)**, ahead of their originally-planned Phase 3 scheduling — see the "Lead Endpoints" section below for the real, as-built shape (which diverges from this doc's original path sketch the same way Client's real implementation does — see the note there).

---

## Scope

Client management (MVP) + Lead/Site Visit (Phase 3). All endpoints are company-scoped: `{companyId}` is resolved server-side from the authenticated session's active membership, never trusted from the URL/body alone (the server still validates the path value matches the resolved membership).

## Client Endpoints (MVP)

| Method | Path | Purpose | Permission |
|---|---|---|---|
| GET | `/companies/{companyId}/clients` | List clients (filter: search, has active projects) | `client.view` |
| POST | `/companies/{companyId}/clients` | Create client | `client.create` |
| GET | `/companies/{companyId}/clients/{clientId}` | Client 360 view (basic info, projects, quotations, invoices, payments, documents, notes, activity) | `client.view` |
| PATCH | `/companies/{companyId}/clients/{clientId}` | Edit client | `client.edit` |
| DELETE | `/companies/{companyId}/clients/{clientId}` | Soft-delete client (blocked if active projects exist) | `client.delete` |
| GET | `/companies/{companyId}/clients/{clientId}/projects` | Projects for this client | `client.view`, `project.view` |
| POST | `/companies/{companyId}/clients/{clientId}/notes` | Add internal note | `client.edit` |

*(As-built note, applies identically to Lead below: every implemented module in this codebase resolves `{companyId}` from the authenticated session server-side and does not carry it as a URL path segment — the real routes are bare, e.g. `/clients`, `/clients/{clientId}`, not `/companies/{companyId}/clients`. This doc's path sketches were never retrofitted after implementation; treat the path *shape* (resource nesting, sub-actions) as accurate and the literal `/companies/{companyId}/...` prefix as pre-implementation planning shorthand.)*

## Lead Endpoints (Phase 3 — implemented 2026-09-15, BE-061)

| Method | Path | Purpose | Permission |
|---|---|---|---|
| GET | `/leads` | List leads (filter: `status`, `assignedTo`; search: name/companyName/email/mobile; `ordering`) | `lead.view` |
| POST | `/leads` | Create lead (always starts at status `new`) | `lead.create` |
| GET | `/leads/{leadId}` | Retrieve lead | `lead.view` |
| PATCH | `/leads/{leadId}` | Update lead's identity/assignment/notes fields (no `status` here) | `lead.edit` |
| DELETE | `/leads/{leadId}` | Soft-delete lead | `lead.delete` |
| PATCH | `/leads/{leadId}/status` | Move status forward one step, or to `lost`. `won` is never reachable here — see `/convert` | `lead.edit` |
| POST | `/leads/{leadId}/mark-lost` | Mark lost — requires `lossReason`, optional `followUpReminderAt` | `lead.edit` |
| POST | `/leads/{leadId}/convert` | Convert lead → client (+ optionally create project via `createProject`/`projectName`). Idempotent — re-calling on an already-converted lead returns the existing result unchanged | `lead.convert` |

Status vocabulary (`apps/leads/models.py::LeadStatus`): `new → qualified → follow_up → site_visit_scheduled`, plus side-states `lost` (reachable from any non-terminal status) and `won` (reachable *only* via `/convert`, never via the plain `/status` endpoint — converting has real side effects that a bare status flip must never be able to skip).

## Site Visit Endpoints (Phase 3)

| Method | Path | Purpose |
|---|---|---|
| GET | `/companies/{companyId}/site-visits` | List site visits |
| POST | `/companies/{companyId}/site-visits` | Schedule a site visit (against lead or client/project) |
| PATCH | `/companies/{companyId}/site-visits/{visitId}` | Update visit (assign, capture measurements/requirements/photos/notes) |
| POST | `/companies/{companyId}/site-visits/{visitId}/report` | Submit site visit report (may trigger project creation) |

## Notes

- Client deletion should be blocked (or require explicit force + cascade confirmation) when the client has projects, quotations, or invoices — see `Database_Schema.md` FK constraint guidance (`ON DELETE RESTRICT`).
- Lead-to-client conversion should be idempotent and auditable (`audit_log` entry), since it changes the commercial status of a prospect.
