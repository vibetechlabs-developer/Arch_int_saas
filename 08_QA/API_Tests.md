# API Tests

**Status:** Draft. Layer 3 of `Test_Strategy.md`'s pyramid — verifies the actual HTTP contract every endpoint in `04_API/` promises, matching `00_Development_Standards/API_Response_Format.md` exactly.

---

## 1. Scope

An API test sends a real HTTP request to a running instance of the Django/DRF application (in-process test client is fine — doesn't need a deployed server) and asserts on the **HTTP response**: status code, envelope shape, headers — not internal state (that's `Integration_Tests.md`'s job, though the same test file may assert both where convenient).

## 2. Tooling

- DRF's `APIClient` (via `pytest-django`) for the primary suite — fast, in-process, runs in the same CI job as integration tests.
- Optional: a schema-based contract tool (e.g. `schemathesis`, generating requests from the DRF-generated OpenAPI schema) to catch undocumented-endpoint drift between `04_API/` specs and actual implementation — run as a scheduled/pre-release check, not on every PR (too slow for the fast-feedback gate).

## 3. What Every API Test Suite Must Cover Per Endpoint

1. **Happy path** — valid request → correct status code (`00_Development_Standards/API_Response_Format.md` §3) and response shape (§1).
2. **Envelope conformance** — every response (success or error) has `success`, `data`/`error`, and `requestId` fields exactly as specified; list endpoints have `pagination`.
3. **Validation failure** — malformed/missing fields → `400` with `VALIDATION_ERROR` code and populated `details` array (`00_Development_Standards/Validation_Standards.md` §7).
4. **Auth failure** — no/expired token → `401`.
5. **Permission failure** — authenticated but wrong role → `403` (`05_Security/Permissions.md`).
6. **Tenant boundary** — resource belongs to another company → `404`, never `403` or `200` (`00_Development_Standards/Error_Handling.md` §5 — this is the API-layer half of the tenant isolation test; `Integration_Tests.md` §3.1 covers the same property from the data-access side).
7. **Conflict/business-rule cases** — e.g. approving an already-approved quotation → `409`/`422` with the correct `code`.
8. **Idempotency** — for endpoints flagged idempotent in `00_Development_Standards/API_Response_Format.md` §8 (e.g. `POST /invoices/{id}/send`), a retried request produces the same end state, not a duplicate side effect.

## 4. Priority Modules (highest financial/security stakes)

- **Finance API** (`04_API/Finance_API.md`) — Quotation approve/reject/revise, Invoice send/cancel, Payment record/void, Expense workflow transitions. Every status transition endpoint gets a full matrix test (legal transition → succeeds, illegal transition → `422`).
- **Authentication API** (`04_API/Authentication_API.md`) — token issuance/refresh/expiry, invitation accept flow, platform-admin vs. company-user token separation (assert a platform-admin token is rejected on company endpoints and vice versa, per `05_Security/JWT.md` §6).
- **BOQ API** (`04_API/BOQ_API.md`) — server-side `amount = quantity × rate` recomputation even when the client sends a different value (`00_Development_Standards/Validation_Standards.md` §3).

## 5. Contract Drift Detection

Whenever a `04_API/` spec doc and the actual DRF endpoint disagree, that's a bug in one of the two — either the code needs to catch up to the documented contract, or the doc needs to be updated in the same PR (`00_Development_Standards/Code_Review_Checklist.md` §7). API tests asserting against the documented contract are what catches this drift automatically instead of relying on someone noticing.

## 6. CI Integration

Runs alongside `Integration_Tests.md` (same test-database CI job, since both need a running Django app + test DB) — see `07_DevOps/CI_CD.md`.
