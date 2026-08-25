# Tenant Isolation (Draft)
## INT Projects — Multi-Company Interior & Architecture Management SaaS

**Status:** Draft — this is the single most important security requirement in the source document and must be treated as a hard invariant, not a best-effort guideline.

---

## 1. The Rule

From the source requirements: **"Company A must never be able to access Company B's data."** All company-owned records must be tenant-scoped, and this must be enforced server-side — the frontend is explicitly called out as untrusted for this purpose.

## 2. Mandatory Request Flow

Every request touching company-owned data must pass through this exact sequence before business logic runs:

```
Request
 → Authentication (validate token, identify user)
 → Identify Company (from the request's company context, e.g. path param)
 → Check Membership (does this user have an active company_membership for this company?)
 → Check Permission (does this user's role in this company grant the requested action?)
 → Tenant-Scoped Data Query (every query filtered by company_id)
 → Business Logic
 → Response
```

If **any** step fails, the request is rejected — there is no partial/degraded success path.

## 3. Implementation Layers (defense in depth)

1. **Middleware layer** — a single, mandatory piece of middleware (not opt-in per-route) that resolves company membership and attaches the verified `company_id` to the request context. Business logic never reads a company ID from anywhere else.
2. **Query layer** — every data-access function for a tenant-owned table takes `company_id` as a required parameter (not optional), ideally enforced by the type system/query builder so it's impossible to compile/write a query that omits it.
3. **Database layer (recommended backstop)** — consider PostgreSQL Row-Level Security (RLS) policies keyed on `company_id`, set via a session variable at the start of each request's DB connection. This means even a bug in the application/query layer cannot leak cross-tenant rows, because the database itself refuses to return them. See `02_Architecture/Technical_Architecture.md` §8 for this as an open decision.
4. **Schema layer** — `company_id NOT NULL` on every tenant-owned table (see `03_Database/Naming_Standards.md`), so a row without tenant ownership cannot exist.

## 4. What Must Never Happen

- A request body or query string parameter named `companyId` must never be trusted as the authorization boundary by itself — it may be present for readability/routing, but the actual authorization decision is always "does this authenticated user have an active membership in this company," verified server-side.
- No endpoint should support a "list across all companies" query for a company-scoped resource, except explicitly on the Platform Admin surface, which is a structurally separate API surface (see `04_API/Authentication_API.md`).
- Caching layers (if introduced) must key cache entries by `company_id` — never share a cache entry for "all clients" across tenants.

## 5. Testing Requirement

Tenant isolation should have dedicated automated tests (see `08_QA/Test_Cases.md`) that assert: a user authenticated for Company A receives a 403/404 (not empty data, not another company's data) when attempting any read or write against Company B's resources by ID, even if they guess or enumerate a valid UUID.

## 6. Platform Super Admin Exception

The Platform Super Admin operates outside this model entirely (see `04_API/Authentication_API.md` and `05_Security/Permissions.md`) — their access to company data, if ever needed for support purposes, must go through an explicit, audited "support access" path, not the same tenant-scoped endpoints, and must itself be logged in `audit_log`.
