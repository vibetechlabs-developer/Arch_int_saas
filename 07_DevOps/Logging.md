# Logging (Infrastructure)

**Status:** Draft. This document covers **log aggregation, retention, and access at the infrastructure level** — how logs are shipped, stored, searched, and who can see them. What a log line actually contains and when code should emit one is defined in `00_Development_Standards/Logging_Standards.md`; that document is the authority on log *content*, this one is the authority on log *infrastructure*. Keep the two in sync rather than duplicating.

---

## 1. Aggregation

Every environment (staging, production) ships structured JSON logs (per `00_Development_Standards/Logging_Standards.md` §1) from both the Django API containers and the frontend's server-side/CDN access logs to a centralized log platform (e.g. the hosting provider's native log aggregation, or a dedicated service like Loki/CloudWatch Logs/equivalent) — never left as unshipped container stdout that disappears when a container recycles.

## 2. Retention

| Log Type | Retention |
|---|---|
| Application logs (info/warn/error) | 30 days hot/searchable, then archived (cheaper cold storage) for 90 more days, then deleted |
| Error-level logs specifically | 90 days hot (errors are referenced longer during incident follow-up and pattern analysis) |
| Access/infrastructure logs (load balancer, container runtime) | 30 days |

This is distinct from `03_Database/Database_Schema.md`'s `audit_log` **table**, which is retained indefinitely per `00_Development_Standards/Logging_Standards.md` §5 and `07_DevOps/Backup_Strategy.md` §1 — operational logs expire, the durable business audit record does not.

## 3. Access Control

Because structured logs routinely include `companyId` and `userId` (`00_Development_Standards/Logging_Standards.md` §1), the log platform itself is access-controlled to engineering/on-call staff only — the same sensitivity that governs direct database access applies here, since a log search is effectively a queryable window into which companies did what, when. Logs are never exposed through any client-facing surface.

## 4. Correlation & Search

- Every incident investigation starts from a `requestId` (from an error-tracking alert per `07_DevOps/Monitoring.md` §2, a support ticket citing the `requestId` shown in an API error response per `00_Development_Standards/API_Response_Format.md` §4, or a user-reported issue) and searches the log platform for that exact ID to pull the full request trail.
- Secondary search dimensions: `companyId` (all activity for a tenant during an incident window), `module` (all activity for a given business module).

## 5. Alerting on Logs

Error-level log volume spikes (distinct from the error-tracking service in `07_DevOps/Monitoring.md` §2, which captures individual exceptions — this is about aggregate volume/rate) feed into the same alerting thresholds as `07_DevOps/Monitoring.md` §3's API error rate metric, since both are downstream signals of the same underlying problem.

## 6. What Must Never Reach the Log Platform

Reiterating `00_Development_Standards/Logging_Standards.md` §3 at the infrastructure level: even with access control in place, secrets/passwords/tokens/full financial account numbers are never logged in the first place — access control on the log platform is a second layer of defense, not a substitute for not logging sensitive data at all.

## 7. Related

- `00_Development_Standards/Logging_Standards.md` — log content standards (what to log, at what level, what fields)
- `07_DevOps/Monitoring.md` — alerting built on top of both logs and dedicated error tracking
- `05_Security/Tenant.md` — why `companyId`-scoped log access control matters as much as database-level tenant isolation
