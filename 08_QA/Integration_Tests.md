# Integration Tests

**Status:** Draft. Layer 2 of `Test_Strategy.md`'s pyramid — exercises real module boundaries with a real (test) database. This is where tenant isolation is proven, not just asserted.

---

## 1. Scope

An integration test exercises **multiple layers together against a real PostgreSQL test database** — a service calling its repository/manager, a Django app's models with actual migrations applied, the tenant/permission middleware pipeline resolving a real request. No database calls are mocked here; that's the entire point of this layer (`Unit_Tests.md` mocks the database, this layer doesn't).

## 2. Tooling

- `pytest-django` with a dedicated test database (created fresh per test run via Django's test runner, migrated using the real migration files from `03_Database/Migration_Plan.md`).
- `factory_boy` factories reused from `Unit_Tests.md` §2, now actually persisting to the test DB.
- Each test wrapped in a DB transaction that rolls back at the end (`pytest-django`'s default `django_db` fixture behavior) so tests don't leak state into each other.

## 3. Priority Integration-Test Targets

### 3.1 Tenant Isolation (highest priority — see `05_Security/Tenant.md`, `08_QA/Test_Cases.md` §1)

This is the **one category of test that must never be satisfied by a unit test alone** — tenant isolation is a property of the real request pipeline (middleware → queryset manager → database), and mocking any of those layers would hide exactly the kind of bug this test exists to catch.

- Create two companies (Company A, Company B) with their own users, clients, projects, invoices via factories.
- Authenticate as a Company A user; attempt to read/write every Company B resource by ID (client, project, quotation, invoice, payment, expense) → assert `404`, never `200` and never `403` (per `00_Development_Standards/Error_Handling.md` §5).
- Assert list endpoints (`GET /companies/{companyId}/clients`, etc.) never return a Company B row even when Company A has zero matching records (an empty correct result, not an accidental cross-tenant leak).
- Assert report/dashboard aggregation endpoints never sum figures across companies.

### 3.2 Cross-Module Data Flow

- Create a Project → BOQ → Quotation → (approve) → Contract → Invoice → Payment chain through the actual service layer calls (not HTTP, this is API-layer territory — see `API_Tests.md`) and assert each downstream entity reflects the correct upstream data (e.g. Invoice total matches the approved Quotation total).
- Expense creation correctly rolls up into a Project's cost summary (`01_Business/FRS.md` §18) when queried immediately after — proves the "reports derived from live transactional data" principle (`02_Architecture/Solution_Architecture.md` §2) actually holds at the DB level, not just in a mocked unit test.

### 3.3 Permission Enforcement Across the Real Membership Model

- A `company_membership` with a given role can/cannot perform an action, verified through the actual `role → role_permission → permission` chain in the test database, not a mocked permission check (`05_Security/Permissions.md`).
- Revoking a membership/role mid-session is reflected on the next request (`05_Security/JWT.md` §3's "resolve fresh from `company_membership`" requirement) — write a test that revokes access between two requests in the same test and asserts the second request is rejected.

### 3.4 Migration Integrity

- Run the full migration sequence from `03_Database/Migration_Plan.md` against an empty database in CI as part of the integration suite — catches a migration that can't apply cleanly before it ever reaches staging.
- For any migration with a data-transforming step (`RunPython`), test both forward and backward (reverse) migration.

## 4. What Integration Tests Are NOT For

- Full user-facing HTTP request/response contract verification — that's `API_Tests.md` (though the two overlap in setup; the distinction is *what's being asserted*: integration tests assert internal state/data correctness, API tests assert the HTTP contract shape).
- Browser-rendered UI behavior — that's `E2E_Tests.md`.

## 5. CI Integration

Runs after unit tests pass, using a dedicated test-database service in the CI job. Tenant-isolation tests specifically are a **required, non-skippable gate** — a failure here blocks merge with no override, per `07_DevOps/CI_CD.md`'s principle that isolation-test failures are a hard merge blocker.
