# Security Tests

**Status:** Draft. Security is tested at every layer of `Test_Strategy.md`'s pyramid, not as a separate bolt-on phase — this document consolidates what's specifically security-focused and adds what the other layers don't cover (dependency scanning, dynamic scanning).

---

## 1. Tenant Isolation — the Highest-Stakes Security Property

Already covered as the top priority in `Integration_Tests.md` §3.1 and `API_Tests.md` §4 — repeated here because it is, per `01_Business/BRS.md` §5, the single hard business requirement that cannot fail under any circumstance. Every new tenant-owned table/endpoint added to the system gets its isolation test written in the same PR that introduces it, not added later (`00_Development_Standards/Code_Review_Checklist.md` §2).

## 2. Authentication & Session Security

- Password reset tokens are single-use and time-limited — test that a used or expired token is rejected.
- Access tokens expire and cannot be used past `exp`; refresh token rotation invalidates the prior refresh token (`05_Security/JWT.md` §4).
- Platform Super Admin tokens (`token_type: platform_admin`) are rejected on every company-scoped endpoint, and company-user tokens are rejected on every platform-admin endpoint (`05_Security/JWT.md` §6) — test both directions explicitly.
- Brute-force protection on login (`RateLimitError`, `00_Development_Standards/Error_Handling.md` §2) — test that repeated failed attempts trigger throttling.

## 3. Authorization / Permission Security

- Every permission code in `05_Security/Permissions.md` §2 has a negative test: a role *without* that permission attempting the action gets `403`, not a silent success or a partial result.
- Revoked permissions take effect immediately on the next request, not after token expiry (`05_Security/JWT.md` §3) — already an `Integration_Tests.md` §3.3 target, cross-referenced here as a security property.

## 4. Input Security

- SQL injection: the Django ORM's parameterized queries are the default defense; any raw SQL (e.g. RLS policy setup, complex report queries) is specifically reviewed and tested for injection safety, since raw SQL is the one place the ORM's automatic protection doesn't apply.
- XSS: free-text fields (notes, descriptions per `00_Development_Standards/Validation_Standards.md` §6) are stored as-is but the frontend must escape on render — test that a client note containing `<script>` or HTML never executes when displayed.
- File upload validation (`00_Development_Standards/Validation_Standards.md` §6): reject disallowed MIME types and oversized files at the API boundary — test with a spoofed `Content-Type` header, not just a legitimate file.
- Mass-assignment: test that a request body containing extra fields (e.g. a client-supplied `companyId`, `status`, or computed `total` on a create/update request) cannot override server-controlled values (`00_Development_Standards/Validation_Standards.md` §3).

## 5. Dependency & Static Analysis Scanning

| Tool | Scope | Cadence |
|---|---|---|
| `pip-audit` / `safety` | Python/Django dependencies | Every PR (CI gate) |
| `npm audit` (or equivalent) | Frontend dependencies | Every PR (CI gate) |
| `Bandit` | Python static analysis (common security anti-patterns) | Every PR |
| `Semgrep` (or ESLint security plugin) | TypeScript/React static analysis | Every PR |

A known-critical vulnerability in a dependency blocks merge; a known-moderate one is triaged (patch, or documented accepted risk with a follow-up ticket) rather than silently ignored.

## 6. Dynamic Scanning

- **OWASP ZAP baseline scan** against a staging deployment, pre-release — catches missing security headers, obvious misconfigurations, and common web vulnerability classes (not a substitute for the targeted tests above, a backstop for what they might miss).
- Verify security headers are set correctly: `Content-Security-Policy`, `X-Content-Type-Options`, `X-Frame-Options` (or equivalent modern frame-ancestors CSP directive), `Strict-Transport-Security` in production.

## 7. Secrets & Data Exposure

- CI includes a secrets-scanning step (e.g. gitleaks or equivalent) on every push — catches an accidentally committed credential before it reaches `main`, backstopping the manual review guidance in `00_Development_Standards/Git_Strategy.md` §8.
- Log output is scanned/reviewed against `00_Development_Standards/Logging_Standards.md` §3's "never log" list as part of security review for any new logging statement touching an auth/financial code path.
- API error responses are tested to confirm they never leak stack traces or internal details (`00_Development_Standards/Error_Handling.md` §4, `00_Development_Standards/API_Response_Format.md` §2) — a dedicated test asserts an unhandled 500 in a test environment still returns the generic client-safe envelope.

## 8. Cadence

| Check | When |
|---|---|
| Tenant isolation, auth, permission tests | Every PR (part of `Integration_Tests.md`/`API_Tests.md`) |
| Dependency scan, SAST, secrets scan | Every PR |
| OWASP ZAP baseline, full manual security review | Pre-release, and after any change to `05_Security/` implementation |

See `07_DevOps/CI_CD.md` for pipeline wiring and `09_Project/Risk_Register.md` risk #1 (cross-tenant data leakage) for why this category is weighted so heavily.
