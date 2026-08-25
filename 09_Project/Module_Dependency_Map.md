# Module Dependency Map

**Status:** Draft — binding implementation order for Phase 1–2 (MVP). This defines *feature build order*, which is related to but not identical to the *schema build order* in `03_Database/Migration_Plan.md` — see that document's "Dependency Groups" note for where they diverge.

---

## 1. The Rule

**A module may not be started until every module above it in this chain is functionally complete** (API + minimum viable UI + tests passing for its own scope) — not merely "the table exists," but the module actually works end to end.

```
Authentication
     ↓
   Company
     ↓
    User
     ↓
    Role
     ↓
   Client
     ↓
   Project
     ↓
   Product
     ↓
    BOQ
     ↓
 Quotation
     ↓
  Invoice
     ↓
  Payment
     ↓
  Expense
     ↓
  Reports
```

This is the order teams and sprints (`09_Project/Sprint_Planning.md`) are organized around. It exists because every module below the line **reads or writes data owned by a module above it** — starting out of order produces work that has to be redone once the real dependency lands.

## 2. Why Each Link Exists

| Step | Module | Hard Dependency (blocking, FK-based) | Why |
|---|---|---|---|
| 1 | **Authentication** | none | Nothing else can be tested or demoed without a way to log in and hold a session |
| 2 | **Company** | Authentication | A company can't be created/managed without an authenticated actor (even the first Company Owner needs to exist as a user first — see note in §4) |
| 3 | **User** | Company | Users are invited *into* a company (`company_membership`); the membership model needs `company` to exist |
| 4 | **Role** | User | Role assignment happens on a `company_membership`, which needs the `user`/`company` pairing from step 3 |
| 5 | **Client** | Role | Every client-management endpoint is permission-gated (`client.view`/`client.create`/...) — building Client before Role means building it without real authorization, which then has to be retrofitted |
| 6 | **Project** | Client | `project.client_id` is a required foreign key — a project cannot exist without a client to belong to |
| 7 | **Product** | Project | Sequenced here for team focus continuity (Product catalog itself has no FK to Project), but BOQ — the very next module — needs both, so Product must land before BOQ regardless |
| 8 | **BOQ** | Product + Project | `boq_item` references `product`; `boq` references `project` — both must exist and work |
| 9 | **Quotation** | BOQ | Quotation is generated from a project's BOQ (`quotation.boq_id`) and needs `client` (already done in step 5) |
| 10 | **Invoice** | Project + BOQ (+ Quotation) | Per the schema, `invoice` references `contract`/`quotation`, which references `boq`, which references `project` — **an invoice cannot be correctly built without the full chain beneath it already working**, which is why Project and BOQ (and in practice Quotation) must be complete first |
| 11 | **Payment** | Invoice | `payment.invoice_id` is required — there is nothing to pay against otherwise |
| 12 | **Expense** | Project | Only hard-depends on Project (see `Migration_Plan.md` Group H) — sequenced after Payment here so the full commercial/financial chain (Quotation→Invoice→Payment) is proven out before cost-tracking work begins, keeping the team's mental model of "revenue side, then cost side" intact |
| 13 | **Reports** | Project, Quotation, Invoice, Payment, Expense | Reports aggregate live transactional data from every module above (`02_Architecture/Solution_Architecture.md` — "reports derived from transactional data, never separately maintained") — building Reports earlier means building against data that doesn't exist yet |

## 3. Explicit Rules (enforce in sprint planning and PR review)

- **No developer should start Invoice before Project and BOQ are complete.** (And in practice, before Quotation is complete too — Invoice's real dependency chain runs through Quotation/Contract, not around it. Project+BOQ is the floor, not the whole requirement.)
- No developer should start Quotation before Client and BOQ are complete.
- No developer should start Payment before Invoice is complete.
- No developer should start Reports before Quotation, Invoice, Payment, and Expense are all complete — a partial Reports module built against half-finished upstream modules produces numbers nobody can trust, which undermines the entire product's core value proposition (`01_Business/BRS.md` §2).
- Expense may be started in parallel with Quotation/Invoice/Payment (they share no hard dependency beyond Project) **if the team has capacity to split**, but Reports still waits for all of them to finish, per the rule above.
- Product may be started in parallel with Client/Project work once Company exists, since Product's only real dependency is `company`, not `project` — the sequencing above is for team focus, not a hard blocker, and can be relaxed if a second developer is free.

## 4. Bootstrapping Exception

Step 2 (Company) and step 3 (User) have a chicken-and-egg relationship in practice: the very first "user" in the system (a Platform Admin creating the first company + its Owner) is created through a seed/bootstrap process, not through the normal "invite a user into an existing company" flow that steps 2–4 otherwise assume. Document this bootstrap path explicitly when Authentication + Company are built — it's the one place in the dependency chain where the normal order doesn't literally apply.

## 5. Relationship to Other Documents

- `03_Database/Migration_Plan.md` — schema-level build order (which can run slightly ahead of or in parallel with this feature order, per its Dependency Groups note)
- `09_Project/Roadmap.md` — this entire chain is Phase 1–2; Phase 3+ modules (Lead, Site Visit, Design, Procurement, Site Management, Snags, Handover, Client Portal) attach onto this chain at defined points once scheduled (e.g., Lead precedes Client in the *expanded* future flow, but is out of scope until Phase 3)
- `00_Development_Standards/Code_Review_Checklist.md` — a PR that implements a module out of this order (e.g. an Invoice endpoint opened before Quotation is merged) should be flagged in review, not just quietly accepted because the code compiles
