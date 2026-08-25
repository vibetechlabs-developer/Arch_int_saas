# Backup Strategy

**Status:** Draft.

---

## 1. What Gets Backed Up

| Data | Method | Why |
|---|---|---|
| PostgreSQL (system of record — every business table) | Automated daily full snapshot + continuous WAL archiving for point-in-time recovery | This is the entire business — clients, projects, quotations, invoices, payments, expenses. Total loss here is not recoverable from anywhere else. |
| Object storage (design files, drawings, receipts, attachments) | Provider-level versioning + cross-region replication where available | These files often have no other copy — a client's uploaded design or a scanned receipt exists only here. |
| `audit_log` table | Covered by the same PostgreSQL backup as above, but treated as append-only and never subject to the retention pruning applied to other tables (see §3) | It's the durable compliance record referenced in `01_Business/FRS.md` §27 — pruning it defeats its purpose. |

## 2. Recovery Objectives (initial targets — confirm with client)

- **RPO (Recovery Point Objective):** ≤ 15 minutes of data loss in a worst-case database failure, achieved via continuous WAL archiving rather than relying on the daily snapshot alone.
- **RTO (Recovery Time Objective):** production database restorable and serving traffic within 4 hours of a declared incident.

These are starting targets, not guarantees — they should be validated against what the managed Postgres provider chosen in `07_DevOps/Production.md` §6 actually offers, and tightened once real usage/SLA commitments to the client are established.

## 3. Retention Policy

| Backup Type | Retention |
|---|---|
| Daily snapshots | 30 days |
| Weekly snapshots | 12 weeks |
| Monthly snapshots | 12 months |
| `audit_log` table specifically | Never pruned by this policy — retained indefinitely unless a specific legal retention limit is confirmed with the client (`07_DevOps/Production.md` §6 item 3) |

Financial records (invoices, payments, expenses) may be subject to a jurisdiction-specific legal retention minimum — this is an open item (`07_DevOps/Production.md` §6) to confirm with the client before finalizing this table's numbers, since the answer could extend some of the periods above.

## 4. Restore Testing

A backup that has never been restored is not a verified backup. **Quarterly restore drill:** restore the most recent snapshot into an isolated environment and verify the application boots against it and key tenant-isolation/financial-integrity spot-checks pass (reuse a subset of `08_QA/Integration_Tests.md` assertions against the restored data) — not just that the restore command exits successfully.

## 5. Object Storage Backup Detail

- Versioning enabled on the bucket so an accidental overwrite/delete of a design file or receipt is recoverable, consistent with `01_Business/FRS.md` §20's requirement that design files be version-controlled rather than overwritten.
- Deleted-object retention (soft-delete window) of at least 30 days before permanent deletion, giving a recovery window for accidental deletes initiated through the application.

## 6. Company Offboarding

When a company/tenant is offboarded (per `01_Business/FRS.md` §1 platform admin responsibilities), its data is retained in backups for the standard retention period above even after the live records are removed/archived from the primary database — a company that churns and later disputes data handling still has a recovery window, not immediate irreversible deletion.

## 7. Related

- `07_DevOps/Production.md` §2 — where the managed database backup features actually get configured
- `07_DevOps/Rollback_Process.md` — application-level rollback, distinct from data restoration (a bad deploy is fixed by rollback, not by restoring a database backup, which is reserved for actual data loss/corruption)
