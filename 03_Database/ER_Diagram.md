# ER Diagram (Conceptual)
## INT Projects — Multi-Company Interior & Architecture Management SaaS

**Status:** Draft — conceptual only. Physical schema is in `Database_Schema.md`; both are pending client approval of the business/functional requirements.

---

## 1. Conceptual Entity Relationship (MVP scope: Phase 1–2)

```mermaid
erDiagram
    PLATFORM ||--o{ COMPANY : hosts
    COMPANY ||--o{ USER : employs
    COMPANY ||--o{ CLIENT : owns
    COMPANY ||--o{ PRODUCT : catalogs
    USER }o--o{ ROLE : "assigned via membership"
    ROLE ||--o{ PERMISSION : grants
    CLIENT ||--o{ PROJECT : commissions
    PROJECT ||--o{ BOQ : has
    BOQ ||--o{ BOQ_ITEM : contains
    BOQ_ITEM }o--|| PRODUCT : references
    PROJECT ||--o{ QUOTATION : has
    QUOTATION ||--o{ QUOTATION_ITEM : contains
    QUOTATION ||--o| BOQ : "derived from"
    QUOTATION ||--o| CONTRACT : "on approval generates"
    PROJECT ||--o{ INVOICE : has
    INVOICE ||--o{ INVOICE_ITEM : contains
    INVOICE ||--o{ PAYMENT : receives
    PROJECT ||--o{ EXPENSE : incurs
    PROJECT ||--o{ TASK : has
    PROJECT ||--o{ DOCUMENT : has
    PROJECT }o--o{ USER : "assigned team"
    COMPANY ||--o{ AUDIT_LOG : records
```

## 2. Conceptual ER (Phase 3+ additions, for future reference)

```mermaid
erDiagram
    LEAD ||--o| CLIENT : "converts to (on Won)"
    LEAD ||--o{ SITE_VISIT : schedules
    PROJECT ||--o{ SITE_VISIT : schedules
    PROJECT ||--o{ DESIGN : has
    DESIGN ||--o{ DESIGN_VERSION : versions
    PROJECT ||--o{ PURCHASE_REQUEST : raises
    PURCHASE_REQUEST ||--o| PURCHASE_ORDER : approved_to
    PURCHASE_ORDER }o--|| VENDOR : issued_to
    PROJECT ||--o{ SITE_DAILY_LOG : logs
    PROJECT ||--o{ SNAG : has
    PROJECT ||--o| HANDOVER : completes_to
```

## 3. Key Relationship Rules

- Every entity below `COMPANY` in the hierarchy carries a `company_id` foreign key (tenant scope), enforced at the schema level — see `Database_Schema.md` and `05_Security/Tenant.md`.
- `CLIENT` is reusable across multiple `PROJECT`s within the same company (many projects → one client).
- `PROJECT` is the aggregation root for BOQ, Quotation, Contract, Invoice, Expense, Task, Document, and (future) Design/Site Activity/Snags.
- `QUOTATION` references its source `BOQ` (optional — a quotation may be created without a formal BOQ) and, once approved, may generate a `CONTRACT`.
- `INVOICE` is generated from an approved `QUOTATION`/`CONTRACT` and accumulates zero or more `PAYMENT`s (supports partial payment).
- `USER` ↔ `ROLE` is a many-to-many relationship scoped through **company membership** — the same person could theoretically hold different roles in different companies (e.g., a freelance accountant), so the membership record (not the user record) carries the role.

## 4. Notes

- This is a conceptual diagram to align on entities and relationships before physical schema design. It intentionally omits columns, types, and indexes — see `Database_Schema.md`.
- Do not finalize the physical schema until the Requirement Approval Gate items in `01_Business/BRS.md` §9 are signed off, since role/permission granularity and BOQ/quotation versioning rules directly affect table design.
