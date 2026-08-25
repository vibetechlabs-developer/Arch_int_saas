# API Response Format

**Priority:** Highest. Every endpoint in `04_API/` must conform to this envelope — no per-module exceptions.

---

## 1. Success Envelope

### Single resource

```json
{
  "success": true,
  "data": {
    "id": "inv_5e6f...",
    "invoiceNumber": "INV-2026-0042",
    "status": "partially_paid",
    "total": 400000,
    "paid": 250000,
    "due": 150000
  },
  "requestId": "req_9f2c..."
}
```

### Collection (paginated)

```json
{
  "success": true,
  "data": [ { "id": "proj_1..." }, { "id": "proj_2..." } ],
  "pagination": {
    "page": 1,
    "pageSize": 25,
    "totalItems": 118,
    "totalPages": 5
  },
  "requestId": "req_9f2c..."
}
```

- Pagination is **required** on every list endpoint from day one — never ship an unpaginated list "for now," since companies will accumulate hundreds/thousands of clients, projects, invoices.
- Query params: `?page=1&pageSize=25` (defaults: `page=1`, `pageSize=25`, max `pageSize=100`).
- List endpoints additionally accept documented filter params per module (e.g. `?status=&clientId=&dateFrom=&dateTo=` — see each spec in `04_API/`).

## 2. Error Envelope

```json
{
  "success": false,
  "error": {
    "code": "INVOICE_ALREADY_PAID",
    "message": "This invoice has already been fully paid.",
    "details": []
  },
  "requestId": "req_9f2c..."
}
```

- `code` — stable, `UPPER_SNAKE_CASE`, machine-readable, namespaced by nothing extra (module context is usually obvious from the endpoint) — this is what the frontend switches on, not `message`.
- `message` — human-readable, safe to display, in English (localization layer, if any, translates by `code`, not by re-parsing `message`).
- `details` — populated for validation errors (`Validation_Standards.md` §7); empty array otherwise.
- Never include a stack trace, internal error class name, file path, or raw database error text — see `Error_Handling.md` §4.

## 3. HTTP Status Code Mapping

| Status | Meaning | Source |
|---|---|---|
| 200 | Success (GET, or a mutation returning the updated resource) | |
| 201 | Resource created | POST that creates a new entity |
| 204 | Success, no body | DELETE, or an action with nothing meaningful to return |
| 400 | `ValidationError` | `Error_Handling.md` §2 |
| 401 | `AuthenticationError` | |
| 403 | `PermissionError` | |
| 404 | `NotFoundError` (including cross-tenant access attempts — see `Error_Handling.md` §5) | |
| 409 | `ConflictError` | |
| 422 | `BusinessRuleError` | |
| 429 | `RateLimitError` | |
| 500 | `InternalError` | |
| 502/503 | `ExternalServiceError` | |

Every response — success or error — always sets the HTTP status to match the envelope's actual outcome; never return `200` with `"success": false` in the body.

## 4. `requestId` Is Always Present

Every response, success or error, includes the same `requestId` that appears in the server-side structured logs for that request (`Logging_Standards.md` §1) — this is what a support ticket or bug report references to pull the exact log trail, without needing timestamps or guesswork.

## 5. Field Naming in Responses

- `camelCase` for all JSON fields, regardless of `snake_case` column names in PostgreSQL (`03_Database/Naming_Standards.md`) — the API layer is the translation boundary; never leak raw DB column names into the response.
- Dates/timestamps: ISO 8601 with timezone (`2026-08-24T10:15:30.123Z`), never a bare date-only string for a `TIMESTAMPTZ` field, and never epoch millis.
- Money: always a number in the smallest sensible unit for the currency's precision as documented per company (e.g. rupees with 2 decimal places, not paise/cents as an integer, unless the team later decides otherwise for precision reasons — pick one convention and apply it project-wide, documented here once decided).

## 6. Versioning

- Path-based versioning if/when a breaking change is needed: `/v1/companies/{companyId}/...`. Start unversioned (`/companies/...` implying `v1`) and introduce `/v2/...` only for the specific endpoints that need to break contract — don't version the whole API preemptively.
- A breaking change to an existing endpoint's response shape is never shipped as a silent change — see `Commit_Message_Format.md` §4 `BREAKING CHANGE:` footer requirement and `Code_Review_Checklist.md` §7.

## 7. Empty States

- An empty list is `"data": []` with `"pagination": { "totalItems": 0, ... }` — never `null` or an omitted `data` field.
- A "not found" single-resource GET is a `404` error envelope (§2), never a `200` with `"data": null`.

## 8. Idempotent Actions

Action endpoints that could be retried by a client after a timeout (`POST /invoices/{id}/send`, `POST /invoices/{invoiceId}/payments`) should be safe to retry — either naturally idempotent (re-sending an already-sent invoice is a no-op success, not an error) or support an idempotency key header where a duplicate financial side-effect (e.g. double-recording a payment) would otherwise be possible. See `Error_Handling.md` §6.
