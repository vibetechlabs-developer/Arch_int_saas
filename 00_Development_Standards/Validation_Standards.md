# Validation Standards

**Priority:** Highest.

---

## 1. Principle: Validate at the Boundary, Trust Internally

Every input crosses exactly one validation boundary — the API layer, before it reaches the service/business-logic layer. Once past that boundary, downstream code trusts the shape and type of the data; it does not re-validate defensively. This keeps validation logic in one place per endpoint instead of scattered re-checks.

```
Request → Schema Validation (shape/type/required fields)
        → Business Rule Validation (service layer)
        → Tenant/Permission Check (middleware — NOT validation, see §5)
        → Business Logic
```

## 2. Two Kinds of Validation — Keep Them Separate

| Kind | Where | Example | On Failure |
|---|---|---|---|
| **Schema validation** | API boundary, before the controller's business logic runs | Field required, correct type, string length, valid enum value, valid UUID format | `ValidationError` (400) — see `Error_Handling.md` §2 |
| **Business rule validation** | Service layer, has access to current state/other records | Payment amount ≤ invoice outstanding balance; project status transition is legal; quotation isn't already approved | `BusinessRuleError` (422) — see `Error_Handling.md` §2 |

Never validate a business rule (needs a DB lookup) inside a schema validator, and never leave a pure shape check (is this a string?) to be discovered as a runtime error deep in the service layer.

## 3. Server-Side Computation, Never Client-Trusted

Any value the client could tamper with but that has financial or business-logic significance must be **recomputed server-side**, never taken as given from the request body:

- BOQ item `amount` (`quantity × rate`), and BOQ/Quotation/Invoice `subtotal`/`tax`/`total`.
- Invoice `status` (derived from paid-vs-total and due date), never client-settable directly.
- `company_id` on any tenant-owned write — always resolved from the authenticated session, never accepted from the request body even if present (`05_Security/Tenant.md`).

If a client sends a computed value (e.g. a `total` field for display convenience), the server ignores it for authority and recomputes; a mismatch may be logged as a `warn` (possible client bug or tampering attempt) but never trusted.

## 4. Schema-Based Validation, Not Hand-Rolled `if` Chains

Every endpoint's request body/query/params is validated against a declared schema (co-located per module — `invoice.schema.ts` per `Folder_Structure.md`) rather than ad-hoc `if (!field) throw ...` chains scattered through the controller. This makes the contract in `04_API/` and the actual runtime validation the same source of truth — regenerate/cross-check one against the other rather than letting them drift.

## 5. Tenant/Permission Checks Are Not "Validation"

Resolving `company_id` from membership and checking the caller's permission (`05_Security/Tenant.md`, `05_Security/Permissions.md`) happen in dedicated middleware **before** schema validation of the body, not as a validation rule mixed into the same layer. A request that fails tenant/permission checks never reaches schema validation at all — this ordering matters for the 404-not-403 rule in `Error_Handling.md` §5.

## 6. Sanitization

- Free-text fields (notes, descriptions) stored as-is but always output-encoded on render (frontend responsibility) — never sanitize/strip on input in a way that silently alters what the user typed, since that surprises users and can corrupt legitimate data (e.g. a client's business name with an ampersand).
- File uploads (documents, receipts, designs) validated for allowed MIME types and a size ceiling at the API boundary before ever reaching object storage; filenames are never trusted as storage paths (generate a storage key server-side).

## 7. Consistent Error Shape

Every validation failure returns the standard error envelope (`API_Response_Format.md` §2) with `code: "VALIDATION_ERROR"` and a `details` array listing each failing field and why — enough for the frontend to highlight the specific field, not just a generic banner.

```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Request validation failed",
    "details": [
      { "field": "quantity", "issue": "must be greater than 0" },
      { "field": "clientId", "issue": "required" }
    ]
  },
  "requestId": "req_9f2c..."
}
```

## 8. Numeric & Currency Validation

- Monetary amounts: reject negative values where not meaningful (e.g. quantity, rate), validated as `NUMERIC(14,2)`-compatible (no more than 2 decimal places) before reaching the database, per `03_Database/Naming_Standards.md` §2.
- Dates: `deadline`/`due_date`/`valid_until` fields validated as real calendar dates and, where business-meaningful, checked against related dates (e.g. a project deadline before its start date is a `BusinessRuleError`, not silently accepted).
