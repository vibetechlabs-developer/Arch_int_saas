# Code Review Checklist

**Priority:** Highest. Every reviewer runs through this before approving. Security items (§2) are non-negotiable — a PR cannot be approved with an open item there, no exceptions.

---

## 1. Correctness

- [ ] Does the change do what the PR description claims, and nothing more?
- [ ] Are edge cases handled — empty lists, zero amounts, null/optional fields, boundary dates?
- [ ] For financial code (BOQ/Quotation/Invoice/Payment/Expense): is every total/amount computed server-side, never trusted from client input? (`00_Development_Standards/Validation_Standards.md` §3)
- [ ] Are status transitions (Project, Invoice, Expense, Quotation) validated against the allowed lifecycle graph, not freely settable?

## 2. Security & Tenant Isolation (non-negotiable — see `05_Security/Tenant.md`)

- [ ] Every new/changed query against a tenant-owned table filters by `company_id`.
- [ ] No endpoint trusts a client-supplied `companyId` without verifying it against the authenticated user's actual `company_membership`.
- [ ] New/changed endpoints declare and enforce the correct permission code (`05_Security/Permissions.md`).
- [ ] No secrets, tokens, or credentials introduced in code, config, logs, or test fixtures.
- [ ] Sensitive mutations (invoice, payment, expense, quotation, permission, project changes) write an `audit_log` entry.
- [ ] If this PR is flagged security-sensitive per `Branch_Naming.md` §5, has it had 2 approving reviews?

## 3. Validation & Error Handling

- [ ] Input validated at the API boundary per `Validation_Standards.md`, not assumed valid deeper in the call stack.
- [ ] Errors use the project's error classes/taxonomy (`Error_Handling.md`), not ad-hoc thrown strings or generic exceptions.
- [ ] Error responses match `API_Response_Format.md` — no stack traces or internal details leaked to the client.

## 4. Code Quality & Consistency

- [ ] Naming follows `Naming_Conventions.md` (files, variables, API routes, permission codes).
- [ ] File placement follows `Folder_Structure.md` (controller has no business logic, repository is the only place with raw queries, etc.).
- [ ] No dead code, commented-out blocks, or leftover debug logging/`console.log`.
- [ ] No premature abstraction — a bug fix doesn't need a new framework; three similar lines can stay three lines.
- [ ] Business terminology matches `01_Business/FRS.md` vocabulary (no invented synonyms — `Naming_Conventions.md` §3).

## 5. Logging

- [ ] Follows `Logging_Standards.md` — structured, correct level, no PII/secrets in log payloads.
- [ ] Includes correlation/request ID and, where applicable, `company_id` for traceability.

## 6. Tests

- [ ] New logic has test coverage (unit and/or integration as appropriate).
- [ ] If the change touches tenant-scoping, permissions, or financial calculations, does it include or update a test in the relevant `08_QA/Test_Cases.md` category?
- [ ] Tests actually assert behavior, not just "doesn't throw."
- [ ] CI is green (see `07_DevOps/CI_CD.md`).

## 7. API Contract

- [ ] Response shape matches `API_Response_Format.md` (success envelope, pagination, error envelope).
- [ ] Any breaking change to a request/response contract is called out explicitly in the PR description and commit footer (`Commit_Message_Format.md` §4).
- [ ] Endpoint matches its documented spec in `04_API/`, or that doc is updated in the same PR if the design evolved.

## 8. Documentation

- [ ] If this PR changes a documented business rule, lifecycle, or architecture decision, the relevant doc under `docs/` (`01_Business/` through `09_Project/`) is updated in the same PR — not left to drift.
- [ ] Non-obvious "why" is captured in a code comment only where it wouldn't be obvious from the code itself (no restating what the code already says).

## 9. Database Migrations (if present)

- [ ] Follows `03_Database/Naming_Standards.md`.
- [ ] `company_id NOT NULL` + indexed on every new tenant-owned table.
- [ ] Backward-compatible with currently-deployed code for at least one deploy cycle (`Git_Strategy.md` §7), unless coordinated as a breaking release.

## 10. Reviewer Conduct

- Review the diff for what it *does*, not just what it says it does — read the actual changed lines, don't rubber-stamp based on the PR description.
- If you can't verify a security-relevant claim (e.g. "this is tenant-scoped"), ask for a test that proves it rather than trusting the description.
- Leave actionable, specific comments tied to a line — not general "looks good" approvals on anything touching §2.
