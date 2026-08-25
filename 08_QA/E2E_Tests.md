# End-to-End (E2E) Tests

**Status:** Draft. Layer 4 of `Test_Strategy.md`'s pyramid — the fewest, slowest tests, run against a real browser and a real (deployed preview/staging) build. Proves the whole stack works together the way a user actually experiences it.

---

## 1. Scope & Tooling

- **Tooling:** Playwright — chosen over Cypress for native multi-browser support (Chromium/Firefox/WebKit) and first-class TypeScript support matching the frontend stack (`02_Architecture/Technical_Architecture.md` §2).
- Runs against a deployed preview environment (`07_DevOps/CI_CD.md`) with a seeded test database — never against production, and never mocking the API (that defeats the purpose of this layer; API mocking belongs in `Unit_Tests.md`/frontend component tests).
- Every E2E test starts from a known seeded state (fixture company/users/data) and cleans up after itself, so tests are independently runnable and re-runnable.

## 2. What Belongs at This Layer (and what doesn't)

E2E tests cover **complete user journeys spanning multiple screens**, not per-field validation or per-component behavior (those are covered at lower, faster layers — `Unit_Tests.md`, `Integration_Tests.md`, `API_Tests.md`). If a test could be written at a lower layer and still catch the bug, it belongs there — E2E tests are expensive to run and maintain, so they're reserved for what only an E2E test can prove: that the full stack (frontend + API + DB) actually connects correctly for a real user flow.

## 3. Priority Journeys (mapped to `08_QA/UAT.md`'s business scenarios)

1. **Company onboarding → login → invite user → assign role** — proves the full auth + tenant + permission chain works through the real UI, not just the API.
2. **Client → Project → BOQ → Quotation → Send → Approve** — the core commercial workflow, through the actual Quotation Builder UI (`06_UI/Wireframes.md` "Quotations" screen brief), asserting the live summary panel updates correctly as items are added.
3. **Approved Quotation → Invoice → two partial Payments → status reaches Paid** — proves the financial lifecycle UI reflects the same server-computed status as `API_Tests.md` already verified at the contract level.
4. **Expense submission → approval → shows up in Project cost summary** — proves the "reports derived from live data" principle holds all the way to the rendered Dashboard/Project Overview screen.
5. **Cross-tenant isolation, through the UI** — log in as a Company A user, attempt to navigate directly to a Company B resource URL (not just an API call) → assert the UI shows a proper 404/not-found state (`06_UI/Component_Inventory.md` §12), never a flash of another company's data.
6. **Role-based navigation** — log in as each default role (`05_Security/Permissions.md` §3) and assert the sidebar/actions shown match what that role should see (`06_UI/Application_Shell_Navigation.md` §9) — e.g. a Designer never sees a "Payments" nav item.
7. **Responsive smoke test** — critical journeys (login, dashboard, create-client) re-run at the mobile breakpoint (`06_UI/Responsive_Accessibility.md` §1) to catch layout regressions Playwright's viewport emulation can reach.

## 4. Standards

- Selectors use accessible queries (role, label, text) matching the accessibility work already required in `06_UI/Responsive_Accessibility.md` §2 — not brittle CSS selectors or auto-generated class names. A component that's hard to select in an E2E test is usually also a component with an accessibility gap.
- Every E2E test is independent — no test relies on state left behind by a previous test in the same run.
- Flaky E2E tests get a `retry` budget in CI (Playwright's built-in retry) but a test that's flaky more than occasionally is fixed or removed, per the standard in `Unit_Tests.md` §4 — the same "never quarantine indefinitely" rule applies here even more, since E2E flakiness is expensive to tolerate.

## 5. CI Integration

Runs after unit/integration/API suites pass, against a preview deployment built from the PR (`07_DevOps/CI_CD.md`) — on every merge to `main`, plus a full nightly run against `main` to catch environment drift that only shows up over time (e.g. a third-party dependency update).
