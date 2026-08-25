# Unit Tests

**Status:** Draft. Layer 1 of `Test_Strategy.md`'s pyramid — most numerous, fastest, run on every save/push.

---

## 1. Scope

A unit test exercises **one function/method/component in isolation**, with all collaborators (database, other services, network) mocked or faked. If a test needs a real database connection, it's an integration test (`Integration_Tests.md`), not a unit test — keep the two separated by directory/naming so they can be run independently in CI.

## 2. Backend (Django) — pytest + pytest-django

- **Tooling:** `pytest`, `pytest-django`, `factory_boy` (test data factories, one per model, living alongside the app per `00_Development_Standards/Folder_Structure.md` §2a's `tests/` folder), `pytest-cov` for coverage reporting.
- **What's unit-tested:** `services.py` business logic (the layer named in `Folder_Structure.md` §2a), validators (`00_Development_Standards/Validation_Standards.md`), serializer field-level validation, error-class mapping (`00_Development_Standards/Error_Handling.md`).
- **What's explicitly NOT unit-tested here:** anything requiring a real DB write/read across models, anything requiring the tenant/permission middleware pipeline — those go in `Integration_Tests.md`.
- **Mocking rule:** mock at the boundary of the unit under test (e.g. mock the repository/manager call a service makes), never mock so deep that the test stops proving anything about the unit's actual logic.

### Priority unit-test targets

1. **Financial calculations** — BOQ `amount = quantity × rate`, Quotation subtotal/discount/tax/total, Invoice status derivation from paid-vs-total, Project cost/profit/margin (`01_Business/FRS.md` §12, §13, §18) — every one of these formulas gets exhaustive unit tests including edge cases (zero quantity, 100% discount, overpayment).
2. **Status transition validators** — Project lifecycle, Invoice status, Expense workflow (`00_Development_Standards/API_Response_Format.md` §3, `01_Business/FRS.md` §10, §15, §17) — assert every legal transition succeeds and every illegal one raises `BusinessRuleError`.
3. **Permission/role logic** — pure functions that resolve "does role X have permission Y" (`05_Security/Permissions.md`), tested independently of the HTTP layer.

## 3. Frontend (React/TypeScript) — Vitest + React Testing Library

- **Tooling:** `Vitest` (pairs natively with Vite, per `02_Architecture/Technical_Architecture.md` §2), `@testing-library/react`, `@testing-library/user-event`.
- **What's unit-tested:** individual components from `Component_Inventory.md` (Button states, DataTable sort/filter logic, form validation display, Badge status-to-color mapping), hooks (`apps/web/src/hooks/`), pure utility functions (`apps/web/src/lib/`).
- **Testing Library philosophy:** test what the user sees/does (`getByRole`, `getByLabelText`, `userEvent.click`), never test implementation details (internal state, private methods) — a refactor that doesn't change behavior shouldn't break the test.
- **Snapshot tests:** used sparingly, only for stable, purely-presentational components — never for anything with dynamic data or frequent visual iteration, where snapshot diffs become noise nobody reads.

## 4. Standards

- Test file co-located with the code under test (`Folder_Structure.md` §2, §2a).
- One logical assertion focus per test — a test named `test_invoice_status_updates_on_partial_payment` doesn't also assert unrelated things about the client record.
- Test names describe the behavior, not the implementation: `should_reject_negative_boq_quantity`, not `test_boq_item_1`.
- No test depends on execution order or leftover state from another test — each test sets up its own fixtures/factories.
- Flaky tests are fixed or deleted immediately, never left "quarantined" indefinitely — a flaky test that's ignored is worse than no test, since it trains the team to ignore CI failures.

## 5. CI Integration

Unit tests are the fastest gate in `07_DevOps/CI_CD.md`'s pipeline and run first, before integration/API/E2E — a unit test failure should fail fast, before the slower stages even start.
