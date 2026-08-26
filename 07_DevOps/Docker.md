# Docker / Containerization

**Status:** Implemented (BE-020) — backend stack only. `docker-compose.yml` (repo root) and `backend/Dockerfile` are real, committed files, not indicative snippets. Frontend containerization (`web` service, an nginx-hosted static build) is deferred until `apps/web` exists in this repo — the sections below describe the backend-only stack actually running today: Nginx → Django (Gunicorn) → PostgreSQL, plus Redis → Celery Worker → Celery Beat.

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

## 3. Frontend Dockerfile (`apps/web/Dockerfile`) — Multi-Stage

**Status: still indicative/draft** — no `apps/web` directory exists in this repo yet, so nothing below is implemented. Kept as the target design for whenever frontend work begins; not part of BE-020's scope or verification.

```dockerfile
# --- dev target ---
FROM node:20-slim AS dev
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
CMD ["npm", "run", "dev", "--", "--host"]

# --- builder ---
FROM node:20-slim AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build            # Vite production build → /app/dist

# --- production: static files served via nginx ---
FROM nginx:alpine AS production
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
```

`nginx.conf` handles SPA routing fallback (serve `index.html` for unmatched paths, since this is a client-side-routed React app per `00_Development_Standards/Folder_Structure.md` §3) and proxies `/api/*` to the backend service in non-local environments.

## 4. What's Deliberately Not Containerized

- **PostgreSQL in production** — use a managed service (see `07_DevOps/Production.md` §2), not a self-hosted container; the `postgres` service in §1 is local-dev-only.
- **Object storage** — not present in this compose file at all yet (§1) since no S3-compatible backend is wired into Django settings; a local emulator (e.g. MinIO) or a managed provider is a future addition once that's built (`02_Architecture/Technical_Architecture.md` §8 item 4), not before.

## 5. Related

- `07_DevOps/Development_Environment.md` — full local setup walkthrough using this compose file
- `07_DevOps/CI_CD.md` — how these images are built and pushed in the pipeline
- `07_DevOps/Production.md` — how these images are deployed and run in production
