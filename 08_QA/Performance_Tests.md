# Performance Tests

**Status:** Draft. Layer covering load/response-time behavior — distinct from the correctness-focused layers above, and run on a different cadence (budget checks per-PR, full load tests pre-release).

---

## 1. Why This Matters for This Product Specifically

Two characteristics of this platform make performance testing non-optional rather than a nice-to-have:

1. **Multi-tenant at scale** (`05_Security/Tenant.md`) — every query carries a `company_id` filter; performance must be validated with realistic data volume *per tenant* (hundreds of projects, thousands of invoices) and with *many tenants* in the same database, not a single lightly-populated dev database.
2. **Data-dense tables are the primary interface** (`06_UI/Component_Inventory.md` §3) — the `DataTable` component must stay responsive against real row counts, not just the 5-row demo data used during UI development.

## 2. Backend / API Performance

- **Tooling:** `k6` (scriptable, CI-friendly, good for both smoke and sustained load tests) against a staging environment seeded with realistic data volume.
- **Targets (initial, to validate/adjust with real usage data once live):**
  | Endpoint class | p95 response time |
  |---|---|
  | Single-resource GET (e.g. `GET /invoices/{id}`) | < 200ms |
  | List/search GET with pagination (e.g. `GET /projects`) | < 400ms |
  | Report/dashboard aggregation endpoints | < 800ms |
  | Write endpoints (POST/PATCH) | < 500ms |
- **Load profile:** simulate concurrent requests from multiple companies simultaneously (not one company at a time) — this is the realistic production shape and the one most likely to surface a missing index on `company_id` or a query that scans more than it should.
- **Database query review:** every list/report endpoint reviewed for `N+1` query patterns (Django ORM's `select_related`/`prefetch_related`) as part of the PR that introduces it (`00_Development_Standards/Code_Review_Checklist.md`), not caught only at load-test time.

## 3. Frontend Performance

- **Tooling:** Lighthouse CI, run against key screens (Dashboard, Client list, Project detail) in the CI pipeline as a budget check.
- **Budgets (initial targets):**
  - Largest Contentful Paint < 2.0s on a throttled "Fast 3G"/mid-tier mobile profile
  - Total JS bundle for the initial route < 250KB gzipped (route-based code-splitting per `06_UI/Application_Shell_Navigation.md`'s feature-based frontend structure keeps this achievable)
  - No unbounded client-side rendering of an entire unpaginated list — every `DataTable` (`06_UI/Component_Inventory.md` §3) is server-paginated per `00_Development_Standards/API_Response_Format.md` §1, never rendering thousands of rows in the DOM at once.
- **Animation performance:** motion (`06_UI/Design_Tokens.md` §6) is implemented with GPU-friendly properties (`transform`/`opacity`) only, never triggering layout thrash — verified via browser performance profiling on the priority journeys from `E2E_Tests.md` §3.

## 4. Database Performance

- Every `company_id` column and every foreign key indexed (`03_Database/Naming_Standards.md` §3) — verified via `EXPLAIN ANALYZE` on the highest-traffic queries as part of pre-release performance review, not assumed correct from the schema alone.
- Report queries (`04_API/Finance_API.md` Reports endpoints) tested against a seeded dataset sized to a realistic "mature company" (e.g. 2+ years of invoices/expenses/projects) before shipping, since these are the queries most likely to degrade with data growth.

## 5. When Performance Tests Run

- **Budget checks** (Lighthouse CI thresholds, k6 smoke test with light load) — every PR, fast enough to be a normal CI gate (`07_DevOps/CI_CD.md`).
- **Full sustained load test** — pre-release, against a staging environment sized close to expected production load, not on every PR (too slow/expensive for that cadence).

## 6. What This Is Not

Performance testing here is not premature optimization — it's validating the specific architectural promises already made elsewhere in this doc set (tenant-scoped indexing in `03_Database/Naming_Standards.md`, live-computed reports in `02_Architecture/Solution_Architecture.md`) actually hold under realistic load, before a real customer discovers otherwise.
