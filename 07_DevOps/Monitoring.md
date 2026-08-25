# Monitoring

**Status:** Draft.

---

## 1. Scope

Three distinct concerns, each needing its own tooling: **error tracking** (something broke), **infrastructure metrics** (the system is under strain), and **uptime/availability** (is it reachable at all). `07_DevOps/Logging.md` covers structured log aggregation/search separately — monitoring is about detecting and alerting on problems, logging is about being able to investigate them once detected.

## 2. Error Tracking

- **Tooling:** an application error-tracking service (e.g. Sentry) integrated on both the Django backend and the React frontend.
- Every `InternalError`/unhandled exception (`00_Development_Standards/Error_Handling.md` §7) is automatically captured with the same `requestId`, `companyId`, `userId` context that appears in structured logs (`00_Development_Standards/Logging_Standards.md` §1) — so an error-tracking alert and a log search for the same incident are cross-referenceable by `requestId`.
- Frontend errors (React error boundaries, unhandled promise rejections) are captured too — an error a user hits that never reaches the API (a frontend bug) is otherwise invisible to backend-only monitoring.

## 3. Infrastructure Metrics

| Metric | Alert Threshold (initial) |
|---|---|
| API container CPU/memory | Sustained > 80% for 5+ minutes |
| PostgreSQL connection count | > 80% of `max_connections` (ties to the pooling requirement in `07_DevOps/Production.md` §2) |
| PostgreSQL query latency (p95) | > 2× the baseline for the affected query class |
| API error rate (5xx responses) | > 1% of requests over a 5-minute window |
| API p95 response time | Exceeds the targets set in `08_QA/Performance_Tests.md` §2 by 50%+ sustained |
| Object storage error rate | Any sustained non-zero rate (uploads/downloads failing is immediately user-visible and often financially relevant — receipts, designs) |

## 4. Uptime Monitoring

External synthetic check (a simple authenticated health-check ping, e.g. every 1–5 minutes) against the production API and frontend from outside the hosting provider's own network — catches a total outage that internal metrics alone might not (e.g. a DNS or load-balancer failure upstream of the app tier itself).

## 5. Security-Relevant Monitoring

Beyond generic infra health, specifically alert on:
- A spike in `403`/`404` responses on company-scoped endpoints from a single user/session — a plausible signal of tenant-boundary probing, worth a look even though the system is designed to correctly reject it (`05_Security/Tenant.md`).
- Repeated authentication failures from a single source (ties to the brute-force protection tested in `08_QA/Security_Tests.md` §2).
- Any error in the tenant/permission middleware pipeline itself (`05_Security/Tenant.md` §2) — this code path failing open would be a critical incident, not a routine error.

## 6. Dashboards

A small set of role-relevant dashboards, not one giant board nobody reads:
- **On-call/engineering:** error rate, latency, infra metrics from §3.
- **Business/ops (optional, later):** active companies, request volume trends — operational, not the client-facing product dashboard defined in `06_UI/Wireframes.md`.

## 7. Alert Routing

Alerts route to whoever is on call, with severity-based channels (e.g. a page for uptime/error-rate breaches, a lower-urgency notification for approaching resource thresholds) — avoid alert fatigue by tuning thresholds in §3 based on real observed baselines after launch, not leaving initial guesses in place indefinitely.

## 8. Related

- `07_DevOps/Logging.md` — where the detailed investigation happens once an alert fires
- `07_DevOps/Rollback_Process.md` — the response when monitoring reveals a bad deploy
- `08_QA/Performance_Tests.md` — the performance targets these alerts are measured against
