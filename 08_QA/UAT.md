# User Acceptance Testing (UAT) Plan (Draft)
## INT Projects — Multi-Company Interior & Architecture Management SaaS

**Status:** Draft outline. Detailed scripts pending MVP feature-complete build. This is the acceptance layer of `08_QA/Test_Strategy.md`'s pyramid — see that document for how UAT relates to Unit/Integration/API/E2E/Performance/Security testing.

---

## Purpose

Confirm with the client, in business terms (not technical terms), that the delivered MVP (Phase 1–2) actually answers the business questions listed in `01_Business/BRS.md` §3 and matches the workflow in `02_Architecture/Solution_Architecture.md` §5.

## UAT Scenarios (business-flow level, mapped to source requirements)

1. **Company onboarding** — a new company can be created, its owner can log in, invite an admin and an accountant, and assign roles — without seeing any other company's data.
2. **Client → Project → BOQ → Quotation** — create a client, create a project for them, build a BOQ, generate a quotation from it, send it, and record a client approval.
3. **Quotation → Invoice → Payment** — from an approved quotation, generate an invoice, record two partial payments, and confirm the invoice shows the correct outstanding balance and status.
4. **Expense → Project Cost → Profitability** — submit and approve expenses across categories (materials/labour/other) for a project, and confirm the project's cost summary and profit/margin figures update correctly.
5. **Dashboard accuracy** — confirm the company dashboard KPI cards (Total Projects, Revenue, Received, Pending, Expenses, Net Profit/Loss) match what was entered across scenarios 2–4.
6. **Role boundaries** — log in as a Designer and confirm financial figures (margins/profit) are not visible, per the financial-access permission requirement; log in as an Accountant and confirm they can perform the full financial workflow.
7. **Multi-company isolation** — with two test companies set up, confirm a user in Company A cannot see Company B's clients, projects, or reports under any circumstance, including direct URL/ID manipulation if the client wants to test this themselves.
8. **Reports** — filter reports by date range and by project, and confirm the numbers match manual expectations for the test data entered.

## Sign-off Criteria

Each scenario above should be explicitly walked through with the client (or their nominated tester) and signed off individually — do not treat the whole document as accepted based on a subset of scenarios passing.

## UAT Checklist (per release candidate)

Run through this checklist against the release candidate before it is presented to the client for sign-off. Every box below must be checked before scenario walkthroughs begin — UAT verifies business acceptance, not basic functionality, so the build must already be functionally sound going in.

**Pre-conditions**
- [ ] Release candidate deployed to a UAT/staging environment matching production configuration (`07_DevOps/Staging.md`)
- [ ] All automated test layers green: Unit, Integration, API, E2E (`08_QA/Test_Strategy.md` §4)
- [ ] Security scan pass for this release (`08_QA/Security_Tests.md` §8)
- [ ] Test data seeded: at least 2 companies, with distinguishable data, to make cross-tenant checks visible during walkthroughs
- [ ] Known-issues list (if any) shared with the client tester before the session, so a known limitation isn't mistaken for a new defect

**Scenario walkthroughs** (each item below tracks to a numbered scenario above)
- [ ] 1. Company onboarding
- [ ] 2. Client → Project → BOQ → Quotation
- [ ] 3. Quotation → Invoice → Payment
- [ ] 4. Expense → Project Cost → Profitability
- [ ] 5. Dashboard accuracy
- [ ] 6. Role boundaries
- [ ] 7. Multi-company isolation
- [ ] 8. Reports

**Post-walkthrough**
- [ ] Every defect found during the session logged with severity, not just discussed verbally
- [ ] Client (or nominated tester) signs off each scenario individually, in writing, per §Sign-off Criteria above
- [ ] Any scenario not signed off has an explicit remediation owner and re-test date before the release is considered accepted

## Related

- `08_QA/Test_Strategy.md` — how UAT fits alongside Unit/Integration/API/E2E/Performance/Security testing
- `08_QA/Test_Cases.md` — underlying technical test categories
- `01_Business/BRS.md` §8 — success criteria this UAT plan validates against
