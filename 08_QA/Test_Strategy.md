# Test Strategy — Index

**Status:** Draft. Entry point into the QA documentation set — read this first for the overall pyramid and tooling, then follow the links below for detail per test type. Built against the confirmed stack: React/TypeScript/Vite (frontend), Django/DRF (backend), PostgreSQL (`02_Architecture/Technical_Architecture.md` §2).

---

## 1. The Test Pyramid (this project's shape)

```
                    ▲
                   / \        E2E (fewest, slowest, highest confidence)
                  /___\       — Playwright, full user journeys
                 /     \
                / Integ- \    Integration + API
               /  ration  \   — DRF APIClient, real DB, module boundaries
              /____________\
             /              \
            /   Unit tests    \  Unit (most, fastest)
           /____________________\ — pytest (backend), Vitest (frontend)
```

Most tests are unit tests; fewest are E2E. A bug should be caught at the lowest layer that can catch it — an E2E test asserting a BOQ line-item calculation is a sign the calculation should have a unit test instead, with the E2E test just confirming the page renders the number.

## 2. Documents in This Set

| Doc | Layer | Covers |
|---|---|---|
| `Unit_Tests.md` | Unit | Backend (pytest) and frontend (Vitest) unit test standards |
| `Integration_Tests.md` | Integration | Module-boundary tests with a real database, tenant isolation focus |
| `API_Tests.md` | API/contract | DRF endpoint tests against `04_API/` and `00_Development_Standards/API_Response_Format.md` contracts |
| `E2E_Tests.md` | End-to-end | Playwright, full user journeys through the real UI |
| `UAT.md` | Acceptance | Business-facing scenarios + sign-off checklist (existing doc, business scenarios) |
| `Performance_Tests.md` | Performance | Load/response-time targets, tooling (k6, Lighthouse CI) |
| `Security_Tests.md` | Security | Tenant isolation, auth, dependency scanning, OWASP baseline |
| `Test_Cases.md` | Content (cross-cutting) | The *what to test* catalogue (existing doc) — every layer above draws its assertions from these categories |

## 3. Coverage Philosophy

- **Tenant isolation (`05_Security/Tenant.md`) and financial calculations (BOQ/Quotation/Invoice/Payment totals) are the two areas held to the highest coverage bar** — every code path here needs an explicit test, not incidental coverage from a happy-path test elsewhere.
- No numeric coverage percentage target is treated as meaningful on its own (100% line coverage with no assertions on tenant scoping is worthless) — coverage tooling (`coverage.py`, Vitest's `--coverage`) is used to find **untested code**, not as a pass/fail gate by itself. A minimum floor (e.g. 80% on `core/`, `services.py` files) is a useful smoke alarm, not the goal.
- Every bug fix ships with a regression test reproducing the bug first — per `00_Development_Standards/Code_Review_Checklist.md` §6.

## 4. Where Each Layer Runs

| Layer | Runs | Trigger |
|---|---|---|
| Unit | Locally (fast, `<10s` for a module) + every CI run | Every push, every PR |
| Integration | Locally against a test DB + every CI run | Every push, every PR |
| API | CI, against a fully migrated test DB | Every PR |
| E2E | CI, against a deployed preview/staging build | Every PR merge to `main`, and nightly on `main` |
| Performance | CI (budget checks) + scheduled full load test | Budget checks on PR; full load test pre-release |
| Security | CI (dependency scan, SAST) + scheduled/pre-release (dynamic scan) | Every PR (scan); pre-release (full scan) |

See `07_DevOps/CI_CD.md` for how these stages wire into the pipeline.

## 5. Ownership

A feature is not "done" until its own unit + integration/API tests are written by the developer who built it (`00_Development_Standards/Code_Review_Checklist.md` §6) — QA/E2E authors the cross-module journeys, not the per-module correctness tests, which is the responsibility of whoever wrote the code.
