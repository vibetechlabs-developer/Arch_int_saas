# Docker / Containerization

**Status:** Implemented — local dev (BE-020) and production (Hostinger VPS deployment runbook, 2026-09-23). `docker-compose.yml` (repo root, local dev), `docker-compose.prod.yml` (repo root, production), `backend/Dockerfile`, and `frontend/Dockerfile` are all real, committed files, not indicative snippets. §3 below (frontend containerization) is now implemented, correcting its own earlier "still indicative/draft" status — the real file lives at `frontend/Dockerfile`, not the `apps/web/Dockerfile` path this doc originally sketched (that directory never existed; the real frontend lives at `frontend/`).

---

## 1. Local Development — `docker-compose`

`docker-compose.yml` lives at the **repo root** (not inside `backend/`), so a future `web` service can be added without relocating it. Services: `postgres`, `redis`, `django`, `celery-worker`, `celery-beat`, `nginx`. Full definitions in the file itself — summary:

- **postgres** (`postgres:16-alpine`) — dev-only datastore; `07_DevOps/Production.md` §2 mandates a managed service for real environments, this container never ships there. Named volume `pgdata`, health-checked via `pg_isready`.
- **redis** (`redis:7-alpine`) — Celery broker + result backend today (only consumer; positioned as a future cache layer, not built yet). Not host-exposed. Health-checked via `redis-cli ping`.
- **django** — builds `backend/Dockerfile` target `dev`; bind-mounts `./backend:/app` for hot-reload; `env_file: backend/.env`; overrides `DB_HOST`/`CELERY_BROKER_URL`/`CELERY_RESULT_BACKEND` to container-network values (service names) so the checked-in `.env`'s `localhost` defaults stay correct for non-Docker local runs. Health-checked via `GET /health/` (BE-020's liveness endpoint, `apps/common/views.py::HealthCheckView` — unauthenticated, no DB dependency).
- **celery-worker** / **celery-beat** — same image/build as `django`, only `command:` differs (`celery -A config worker -l info` / `celery -A config beat -l info`). No tasks or schedule are registered yet — pure infra scaffolding ahead of the async workload, not a defect.
- **nginx** (`nginx:alpine`) — reverse proxy in front of Gunicorn; serves `staticfiles`/`media` named volumes directly so Gunicorn workers aren't spending threads on file I/O; config mounted (not baked) from `backend/nginx/nginx.conf`.

`docker compose up` (after `cp backend/.env.example backend/.env`, per `Development_Environment.md` §2) brings up the whole stack. Object storage (MinIO or otherwise) is **not** part of this compose file — no S3-compatible backend is wired into Django settings yet (no `django-storages`, no `AWS_*` config); `MEDIA_ROOT` stays local-filesystem until that's built.

## 2. Backend Dockerfile (`backend/Dockerfile`) — Multi-Stage

Four stages: `base` (shared OS deps) → `dev` (hot-reload target, used by all three app-tier compose services locally) and, separately, `builder` (prod dependencies only) → `production` (slim runtime, no build toolchain, non-root `appuser`). See the file itself for the exact, current implementation — kept here only as a summary so this doc doesn't drift into a second source of truth:

- Split `requirements/dev.txt` (adds `pytest`, `pytest-django`, `factory-boy`) from `requirements/prod.txt` (adds only `gunicorn`) on top of the shared `requirements/base.txt`, so the production image never ships test/dev tooling.
- `production` stage installs `libpq5`/`curl` (runtime libs + the binary the compose healthcheck uses), copies only the installed site-packages from `builder` (not the build toolchain), runs `collectstatic --noinput` while still root (before the ownership handoff, since `STATIC_ROOT` must be writable at that point), then switches to non-root `appuser` — a basic hardening step, not optional.
- **Migrations are deliberately not run inside the Dockerfile or the container's `CMD`** — per `07_DevOps/CI_CD.md` §4, `migrate` is an explicit, isolated deploy step that runs *before* new containers receive traffic, not baked into every container start (which would race concurrent replicas running `migrate` simultaneously). Locally: `docker compose exec django python manage.py migrate`, matching `Development_Environment.md` §2 step 4 exactly.

## 3. Frontend Dockerfile (`frontend/Dockerfile`) — Multi-Stage, Implemented

Three stages, mirroring the backend's own dev/builder/production split: `base` (Node install) → `dev` (hot-reload, `npm run dev -- --host`, used by `docker-compose.yml` if a frontend dev service is ever added there) and, separately, `builder` (`npx tsc && npx vite build --outDir dist`) → `production` (`nginx:alpine`, serves the built static files, no Node runtime shipped).

The `--outDir dist` override is deliberate: `frontend/vite.config.ts`'s own `build.outDir` points *outside* the frontend directory (`../backend/staticfiles/frontend`, a leftover from early scaffolding), which isn't reachable from an isolated frontend-only Docker build context. The flag redirects the build back to a normal local `dist/` inside the image without touching the checked-in Vite config other tooling may still depend on.

`VITE_API_BASE_URL` is baked into the JS bundle at build time from `frontend/.env.production` (Vite's own convention — a static SPA build has no runtime env injection) — edit that file to the real deployed API origin *before* building this image for a real deployment, matching how `.env.development`'s `http://localhost:8000` already works for local dev.

`frontend/nginx.conf` handles SPA routing fallback (`try_files $uri /index.html`, since this is a client-side-routed React app per `00_Development_Standards/Folder_Structure.md` §3) and far-future cache headers for Vite's content-hashed `/assets/` files. It does **not** proxy `/api/*` to the backend — this app's frontend/backend split is cross-origin by design (see `05_Security/Tenant.md` and `CORS_ALLOWED_ORIGINS`), not same-origin-via-path-prefix, so the two are deployed as separate subdomains (e.g. `app.` / `api.`) rather than one origin with a path split.

## 4. Production — `docker-compose.prod.yml` (single-VPS deployment)

Implemented (2026-09-23 Hostinger deployment runbook), a companion to `docker-compose.yml` rather than a replacement — do not run both on the same host. Same six-service shape as local dev (`postgres`, `redis`, `django`, `celery-worker`, `celery-beat`, plus `frontend`, new), with three deliberate differences:

- `django`/`celery-worker`/`celery-beat` build `target: production` (Gunicorn, no dev/test tooling, non-root `appuser` — §2), not `target: dev`.
- Every app-tier port is bound to `127.0.0.1` only (`postgres`/`redis` expose no port to the host at all). Nothing in this compose file is reachable from the public internet directly — a host-level nginx + Certbot (installed on the VPS itself, *not* in this compose file, so a broken app container can never take TLS termination down with it) reverse-proxies the real domains onto these localhost ports. See the deployment runbook for that host nginx config and the one-time Certbot setup.
- No dockerized backend nginx (`backend/nginx/nginx.conf`, §1) — Gunicorn serves `/static/` directly via Whitenoise (`config/settings.py` `MIDDLEWARE`) in production, and `/media/` only matters at all when `STORAGE_BACKEND=local` (recommend `STORAGE_BACKEND=s3` for anything beyond an initial launch — §5). The host-level nginx above is the only reverse-proxy layer in front of Gunicorn in this topology.

**Deviation from §5/Production.md's "managed PostgreSQL" recommendation, disclosed:** self-hosting Postgres (and Redis) in containers here, rather than a managed service, is a deliberate pragmatic choice for a *single-VPS* deployment, where there is no separate managed-database tier to point at. `pgdata` is a named Docker volume with no automated backup — cron a nightly `pg_dump` at minimum until real traffic justifies moving to a managed provider (`07_DevOps/Backup_Strategy.md`).

Migrations are run as an explicit one-off (`docker compose -f docker-compose.prod.yml run --rm django python manage.py migrate`), same discipline as local dev's own §2 note — never baked into a container's start command.

## 5. What's Deliberately Not Containerized

- **PostgreSQL and object storage at real scale** — §4's self-hosted Postgres is a single-VPS MVP choice, not the long-term recommendation; `07_DevOps/Production.md` §2 still describes the managed-service target once traffic/backup requirements justify the move. **Object storage** is genuinely not present in either compose file — no S3-compatible backend is wired into Django settings by default (`STORAGE_BACKEND=local`); set `STORAGE_BACKEND=s3` (fully implemented, BE-078) once a bucket exists, rather than accumulating client files on a single VPS disk.

## 6. Related

- `07_DevOps/Development_Environment.md` — full local setup walkthrough using `docker-compose.yml`
- `07_DevOps/CI_CD.md` — how these images are built and validated in the pipeline (`.github/workflows/ci.yml`'s `docker-build` job builds both the backend and frontend production images on every push, validation only — not pushed to a registry)
- `07_DevOps/Production.md` — the longer-term, larger-scale target architecture (managed Postgres, load balancer, CDN); §4 above is the pragmatic single-VPS path actually deployed today
