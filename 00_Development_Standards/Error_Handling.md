# Error Handling Standards

**Priority:** Highest. Defines the error taxonomy; response shape is specified in `API_Response_Format.md` §2 and must stay in sync with this document.

---

## 1. Principle

Errors are **typed and predictable**, not ad-hoc thrown strings. Every error that can reach the API boundary is an instance of a known error class, so the response layer can map it to the correct HTTP status and client-safe message without guessing.

## 2. Error Taxonomy

| Error Class | HTTP Status | Meaning | Example |
|---|---|---|---|
| `ValidationError` | 400 | Request failed schema/shape validation before business logic ran | Missing required field, wrong type, malformed BOQ item |
| `AuthenticationError` | 401 | No valid session/token | Expired or missing access token |
| `PermissionError` | 403 | Authenticated, but not authorized for this action or company | User lacks `invoice.approve`; company mismatch (see `05_Security/Tenant.md`) |
| `NotFoundError` | 404 | Entity doesn't exist **within the caller's tenant scope** | Requesting an invoice ID that belongs to another company returns 404, not 403 — never confirm existence of another tenant's data (see §5) |
| `ConflictError` | 409 | Request conflicts with current state | Approving an already-approved quotation; duplicate invoice number |
| `BusinessRuleError` | 422 | Structurally valid request that violates a business rule | Recording a payment larger than the invoice's outstanding balance; invalid project status transition |
| `RateLimitError` | 429 | Too many requests | Login attempt throttling |
| `InternalError` | 500 | Unexpected/unhandled failure | Database unavailable, unhandled exception |
| `ExternalServiceError` | 502/503 | A downstream dependency failed | Object storage unreachable, email provider down |

Every module (`invoice`, `quotation`, `expense`, ...) throws these shared classes with module-specific messages/codes — modules do not invent their own parallel error class hierarchy.

## 3. Where Errors Are Created vs. Handled

- **Created** in the service layer (business logic) or validation layer (`Validation_Standards.md`) — never in the repository layer (a DB error is caught and re-thrown as the appropriate typed error, e.g. a unique-constraint violation on invoice number becomes a `ConflictError`, not a raw driver exception).
- **Handled** in exactly one place: a centralized error-handling middleware at the top of the request pipeline. Individual controllers do not catch-and-format errors themselves — they let typed errors propagate up.

```
Route → Controller → Service (throws typed error)
                         ↓
        Centralized Error Middleware (maps error class → HTTP status
        → API_Response_Format.md error envelope → logs per Logging_Standards.md)
```

## 4. What the Client Receives vs. What Gets Logged

- The client receives: HTTP status, a stable machine-readable `code` (e.g. `INVOICE_ALREADY_PAID`), and a human-readable `message` safe to display. See `API_Response_Format.md` §2 for the exact envelope.
- The client **never** receives: stack traces, internal file paths, raw database error text, or any detail that reveals implementation internals or other tenants' data.
- The server logs (per `Logging_Standards.md` §6) the full stack trace, `requestId`, `companyId`, `userId`, and enough context to debug — this is what support/engineering uses, not what ships in the response.

## 5. Tenant-Isolation-Specific Rule

A request for another company's resource by ID must return `404 NotFoundError`, **not** `403 PermissionError` — returning 403 would confirm the resource exists (an information leak about another tenant's data), while 404 gives no signal either way. This is a deliberate, non-negotiable choice tied to `05_Security/Tenant.md` and must be covered by the isolation tests in `08_QA/Test_Cases.md` §1.

## 6. Retry & Idempotency

- `ExternalServiceError`s from downstream dependencies (object storage, email/notification providers) should be retried with backoff at the calling layer before surfacing to the client, where the operation is safely retryable (e.g. a GET, or a write designed to be idempotent).
- Financial mutations (payment recording, invoice generation) must be idempotent where the client might retry after a timeout — use an idempotency key or a pre-check for an existing matching record, never assume a client retry means "do it again."

## 7. Unhandled Errors

Anything not caught as a typed error is treated as `InternalError` (500) by the centralized middleware, logged at `error` level with full context, and returned to the client as a generic "something went wrong" message with the `requestId` for support reference — never the raw exception message or stack.

## 8. Frontend Error Handling

- The frontend maps the API's `code` field (not the `message` string, which may change wording) to user-facing copy, so translations/copy changes don't require frontend logic changes.
- A `403`/`404` on a resource the UI just showed the user (e.g. stale list) should trigger a silent refetch/redirect, not a scary error dialog — distinguish "you're not allowed" from "this genuinely broke."
