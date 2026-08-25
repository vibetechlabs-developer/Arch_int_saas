# Logging Standards

**Priority:** Highest.

---

## 1. Format: Structured, Always

Every log line is a single structured JSON object — never a free-text `printf`-style message alone. This is what makes logs queryable/filterable in production, especially critical in a multi-tenant system where "show me everything that happened for Company X" must be a reliable query.

### Required base fields on every log entry

```json
{
  "timestamp": "2026-08-24T10:15:30.123Z",
  "level": "info",
  "message": "invoice sent to client",
  "service": "api",
  "requestId": "req_9f2c...",
  "companyId": "comp_1a2b...",
  "userId": "usr_7c3d...",
  "module": "invoice",
  "entityId": "inv_5e6f..."
}
```

- `requestId` — generated at the start of every request, propagated through all downstream logs and included in the API error response (`API_Response_Format.md` §3) so a client-reported bug can be traced to its exact log trail.
- `companyId` / `userId` — present on every log entry for a company-scoped request, absent only for genuinely pre-authentication or platform-level log lines.

## 2. Log Levels

| Level | Use For |
|---|---|
| `error` | Unhandled exceptions, failed external calls after retries exhausted, data-integrity violations (e.g. tenant-isolation check failure) — always actionable, always paged/alerted on in production for security-relevant cases |
| `warn` | Recoverable but abnormal — validation failure on a suspicious pattern, retried operation, deprecated endpoint usage |
| `info` | Significant business events — invoice sent, quotation approved, payment recorded, user invited. This is the primary level for business-auditable activity (distinct from, and in addition to, the `audit_log` table which is the durable system-of-record — see §5) |
| `debug` | Detailed flow tracing for development — never enabled by default in production |

Default production log level: `info`. `debug` enabled only temporarily, scoped, and never left on.

## 3. What Must NEVER Be Logged

- Passwords, password hashes, tokens (access/refresh/reset), API keys, or any secret — even partially, even in an error stack trace. Redact before logging if an exception object might contain one.
- Full credit card / bank account numbers, if ever handled — mask to last 4 digits only.
- A client's GSTIN, full address, or other PII should be logged only when operationally necessary (e.g. an error directly involving that record), and never at `debug`-level verbosity in a way that dumps entire client records routinely.
- Raw request/response bodies for financial mutation endpoints (invoice, payment, expense) by default — log the entity ID and the changed fields instead, not the full payload, to avoid accidentally logging sensitive line-item detail at high volume.

## 4. Correlation Across Services

If the platform ever splits into multiple services (`02_Architecture/HLD.md`), `requestId` must be generated at the edge (API gateway or first entrypoint) and passed through every downstream call (headers for HTTP, message metadata for async) so a single business operation is traceable end to end.

## 5. Logging vs. Audit Log — Not the Same Thing

- **Logs** (this document) are operational: for debugging, monitoring, and incident response. They may be sampled, rotated, or expired after a retention window.
- **`audit_log`** (`01_Business/FRS.md` §27, `03_Database/Database_Schema.md`) is the durable, queryable, never-expired business record of who-changed-what for sensitive entities.

A sensitive mutation (invoice, payment, expense, quotation, permission, project change) must **both** emit an `info`-level log line **and** write an `audit_log` row — the log is for ops, the audit row is for the business/compliance record. Don't treat one as a substitute for the other.

## 6. Errors in Logs

Every `error`-level log includes: the error type/class (`Error_Handling.md` §2), a stack trace (server-side only — never sent to the client, per `API_Response_Format.md` §2), and enough context (`companyId`, `entityId`, `module`) to reproduce without needing to ask the user follow-up questions.

## 7. Environment Differences

- **Local/dev:** human-readable pretty-printed logs are fine for developer ergonomics, as long as the underlying structure is the same JSON shape (formatters can pretty-print structured data).
- **Staging/production:** raw structured JSON only, shipped to a centralized log aggregator — never plain-text files with no structure, which are unsearchable at scale and unusable for the tenant-scoped queries this system will need.
