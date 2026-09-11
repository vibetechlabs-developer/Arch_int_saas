# Production Environment

**Status:** Draft — previously blocked on hosting/infra decisions; the technology stack itself is now confirmed (`02_Architecture/Technical_Architecture.md` §2), which is enough to define the topology and operational requirements below. Specific cloud provider/region remains an open decision (§6).

---

## 1. Topology

```
Internet
   ↓
Load Balancer / Reverse Proxy (TLS termination)
   ↓
   ├── Frontend: static build (07_DevOps/Docker.md §3) served via CDN or the nginx image
   └── API: Django/DRF containers (07_DevOps/Docker.md §2), horizontally scaled, behind the same LB
             ↓
        Connection pooler (pgbouncer or equivalent) — see §2
             ↓
        PostgreSQL (managed service — system of record)
             ↓
        Object Storage (managed, S3-compatible) — design files, drawings, receipts, attachments
```

## Object Storage (BE-078)

Implemented — selected via `STORAGE_BACKEND` (`config/settings.py`): `local` (default, `FileSystemStorage`) for development, `s3` for a real deployment. Business apps never touch `django.core.files.storage`/boto3 directly — everything goes through `apps.common.storage`, so the backend stays swappable purely via environment configuration.

- **Public files** (product images, company logos) — a public-read bucket path (`STORAGES["default"]`), permanent unsigned URLs, matching how these have always worked.
- **Private files** (project documents, expense/payment receipts) — a private-ACL bucket path (`STORAGES["private"]`), never a permanently public or persisted-signed URL. Access is only ever through an authenticated, tenant/RBAC-checked proxy endpoint (e.g. `GET /documents/{id}/download`) that either streams the bytes (local backend) or redirects to a short-lived signed URL generated fresh on every request (S3 backend, `AWS_S3_SIGNED_URL_EXPIRE_SECONDS`, default 3600s).
- **Required S3 environment variables** (Django refuses to boot with `STORAGE_BACKEND=s3` if any are missing): `AWS_STORAGE_BUCKET_NAME`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_S3_REGION_NAME`. Optional: `AWS_S3_ENDPOINT_URL` (a non-AWS S3-compatible provider — MinIO, DigitalOcean Spaces, Cloudflare R2), `AWS_S3_CUSTOM_DOMAIN` (a CDN in front of the public bucket only). See `backend/.env.example`.
- **Upload validation**: real decoded-content checks (Pillow for images, PDF magic-byte signature for documents/receipts), never filename/Content-Type — `apps.common.storage.validate_image_upload`/`validate_document_upload`. Max 5 MB (images), 20 MB (documents/receipts, matching nginx's `client_max_body_size`).
- **Retention policy**: a Product image or Company logo is physically deleted from storage when replaced or removed (`ProductService.update_product`/`CompanyService.update_company`, via `transaction.on_commit` so a file is never destroyed before the new DB state actually commits). A Document, Expense receipt, or Payment receipt is **never** automatically deleted, even when its row is soft-deleted or a payment is voided — these may carry audit/compliance value; see open decision §6.3 below on formal retention periods.
- **No Docker volume required for production S3 mode** — `media`/`media_private` (local-mode only) stay unused once `STORAGE_BACKEND=s3` is set via the platform's own environment/secrets.

## 2. Database

- **Managed PostgreSQL** (not self-hosted in a container — `07_DevOps/Docker.md` §4), with automated backups (`07_DevOps/Backup_Strategy.md`), point-in-time recovery enabled, and read replicas considered once report/dashboard query load justifies it (not needed at MVP scale, but the shared-schema multi-tenant design in `02_Architecture/Technical_Architecture.md` §3 means read load *will* grow linearly with tenant count, so this is a near-term scaling lever, not a distant one).
- **Connection pooling** (pgbouncer or the managed provider's equivalent) is required once the API scales beyond a couple of replicas — Django/DRF processes each hold their own connection pool, and without an external pooler, replica count × per-process pool size can exhaust Postgres's `max_connections` faster than expected in a multi-tenant app serving many concurrent companies.
- **Row-Level Security** (if adopted per `02_Architecture/Technical_Architecture.md` §8 item 5) is configured here, applied via a dedicated migration, session-variable-driven per request.

## 3. Application Tier

- API containers run as the `production` Docker target (`07_DevOps/Docker.md` §2), non-root, horizontally scaled behind the load balancer, with health-check endpoints for the orchestrator to use during rolling deploys (`07_DevOps/CI_CD.md` §4).
- Static frontend assets served via CDN where available (lower latency, reduces load on the app tier for pure static content) — falls back to the nginx container (`07_DevOps/Docker.md` §3) if no CDN is provisioned yet.
- TLS terminates at the load balancer; the app tier itself never handles raw HTTP from the public internet.

## 4. Security Headers & Hardening

Per `08_QA/Security_Tests.md` §6: `Content-Security-Policy`, `X-Content-Type-Options: nosniff`, a frame-ancestors/`X-Frame-Options` policy, and `Strict-Transport-Security` are all set at the load balancer or Django's security middleware in production settings (`DEBUG=False`, `ALLOWED_HOSTS` locked to the real domain, `SECURE_*` Django settings enabled).

## 5. Secrets Management

Database credentials, JWT signing keys (`05_Security/JWT.md`), and object storage credentials are injected via the hosting platform's secrets manager (not baked into images, not in `.env` files committed anywhere) — rotated on a defined schedule and immediately on any suspected exposure.

## 6. Open Decisions

1. Cloud provider and region — the source requirements' worked examples use ₹ (INR), suggesting an India-based primary region may be preferable for latency, but this is an inference to confirm with the client, not a decided requirement.
2. CDN provider for frontend static assets.
3. Whether object storage retention for financial documents (invoices, receipts) needs to satisfy a specific legal/tax retention period in the client's jurisdiction — affects `07_DevOps/Backup_Strategy.md` retention policy, not just this document.
4. Autoscaling thresholds for the API tier, once real traffic patterns are known post-launch.

## 7. Related

- `07_DevOps/Backup_Strategy.md`, `07_DevOps/Monitoring.md`, `07_DevOps/Logging.md`, `07_DevOps/Rollback_Process.md` — the operational disciplines that keep this environment healthy
- `05_Security/Tenant.md` — the isolation guarantees this topology must never violate under load or failure
