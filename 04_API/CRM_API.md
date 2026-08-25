# CRM API (Draft)
## INT Projects — Multi-Company Interior & Architecture Management SaaS

**Status:** Draft endpoint sketch. `Lead` and `Site Visit` endpoints are Phase 3 (not MVP) — included here for completeness since they belong to the CRM module conceptually.

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

## Lead Endpoints (Phase 3)

| Method | Path | Purpose |
|---|---|---|
| GET | `/companies/{companyId}/leads` | List leads (filter: status, assigned to) |
| POST | `/companies/{companyId}/leads` | Create lead |
| PATCH | `/companies/{companyId}/leads/{leadId}` | Update lead (qualification/follow-up status) |
| POST | `/companies/{companyId}/leads/{leadId}/mark-lost` | Mark lost — requires loss reason, optional follow-up date |
| POST | `/companies/{companyId}/leads/{leadId}/convert` | Convert lead → client (+ optionally create project) |

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
