# Docker / Containerization

**Status:** Draft — previously blocked on stack selection; unblocked now that `02_Architecture/Technical_Architecture.md` §2 confirms React/TS/Vite + Django/DRF + PostgreSQL.

---

## 1. Local Development — `docker-compose`

```yaml
# docker-compose.yml (indicative)
services:
  postgres:
    image: postgres:16
    environment:
      POSTGRES_DB: int_projects_dev
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
    ports: ["5432:5432"]
    volumes: ["pgdata:/var/lib/postgresql/data"]

  minio:                        # local object storage emulator (S3-compatible)
    image: minio/minio
    command: server /data --console-address ":9001"
    ports: ["9000:9000", "9001:9001"]
    volumes: ["miniodata:/data"]

  api:
    build: { context: ./apps/api, target: dev }
    volumes: ["./apps/api:/app"]     # bind mount for hot-reload
    ports: ["8000:8000"]
    env_file: .env
    depends_on: [postgres, minio]

  web:
    build: { context: ./apps/web, target: dev }
    volumes: ["./apps/web:/app"]
    ports: ["5173:5173"]              # Vite dev server default
    env_file: .env
    depends_on: [api]

volumes:
  pgdata:
  miniodata:
```

`docker compose up` is the single command a new developer runs to get Postgres, object storage, the Django API (hot-reloading via `runserver` or `gunicorn --reload` in the `dev` build target), and the Vite dev server running together — matching the module dependency chain in `09_Project/Module_Dependency_Map.md` §1, since the API needs Postgres before it can serve anything meaningful.

## 2. Backend Dockerfile (`apps/api/Dockerfile`) — Multi-Stage

```dockerfile
# --- base ---
FROM python:3.12-slim AS base
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends libpq-dev gcc && rm -rf /var/lib/apt/lists/*

# --- dev target: hot-reload, dev dependencies included ---
FROM base AS dev
COPY requirements/dev.txt .
RUN pip install --no-cache-dir -r dev.txt
COPY . .
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]

# --- builder: production dependencies only ---
FROM base AS builder
COPY requirements/prod.txt .
RUN pip install --no-cache-dir -r prod.txt

# --- production runtime: slim, no build tools ---
FROM python:3.12-slim AS production
WORKDIR /app
RUN useradd --create-home appuser
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY . .
RUN python manage.py collectstatic --noinput
USER appuser
EXPOSE 8000
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "4"]
```

- Split `requirements/dev.txt` (includes `pytest`, `factory_boy`, debugging tools) from `requirements/prod.txt` (runtime only) so the production image never ships test/dev tooling.
- Runs as a non-root user in production (`appuser`) — a basic hardening step, not optional.

## 3. Frontend Dockerfile (`apps/web/Dockerfile`) — Multi-Stage

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

- **PostgreSQL in production** — use a managed service (see `07_DevOps/Production.md` §2), not a self-hosted container; the `postgres` service above is local-dev-only.
- **Object storage in production** — a managed S3-compatible provider, not the `minio` container above, which is a local emulator only (`02_Architecture/Technical_Architecture.md` §8 item 4).

## 5. Related

- `07_DevOps/Development_Environment.md` — full local setup walkthrough using this compose file
- `07_DevOps/CI_CD.md` — how these images are built and pushed in the pipeline
- `07_DevOps/Production.md` — how these images are deployed and run in production
