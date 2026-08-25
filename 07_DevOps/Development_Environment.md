# Development Environment

**Status:** Draft.

---

## 1. Purpose

The local environment every developer runs on their own machine — fast iteration, hot-reload, disposable data, never connected to any shared/real data.

## 2. Setup

1. Clone the repo.
2. Copy `.env.example` → `.env` (never commit `.env` — see `00_Development_Standards/Git_Strategy.md` §8) and fill in local values (DB credentials matching `07_DevOps/Docker.md` §1's compose defaults are fine locally).
3. `docker compose up` — brings up Postgres, MinIO (local object storage), the Django API (hot-reload), and the Vite dev server (`07_DevOps/Docker.md` §1).
4. `docker compose exec api python manage.py migrate` — applies migrations per `03_Database/Migration_Plan.md`.
5. `docker compose exec api python manage.py seed_dev_data` (or equivalent management command) — seeds a couple of test companies with representative data across every MVP module, so a new developer immediately has something realistic to work against, including **at least two companies** so tenant-isolation behavior is visible from day one, not just a single-tenant happy path.
6. Frontend: `http://localhost:5173`; API: `http://localhost:8000`.

## 3. Developer Workflow

- Backend hot-reloads via Django's dev server watching for file changes; frontend hot-reloads via Vite's HMR — no manual restart needed for either during normal iteration.
- Run the fast test layers locally before pushing: `pytest` (backend unit+integration, `08_QA/Unit_Tests.md`/`Integration_Tests.md`) and `npm run test` (frontend unit, same doc). E2E (`08_QA/E2E_Tests.md`) is normally left to CI given its setup cost, but can be run locally against the dev environment when debugging a specific journey.
- Database resets are cheap and expected — `docker compose down -v && docker compose up` wipes and rebuilds local Postgres from scratch when local data gets into a confusing state; there is no need to preserve local dev data.

## 4. Environment Variables

- `.env.example` is committed and kept up to date as the canonical list of required variables — a new variable added to the app is added to `.env.example` in the same PR, per the general principle in `00_Development_Standards/Code_Review_Checklist.md` §8 (docs/config updated alongside the code that needs them).
- Naming follows `00_Development_Standards/Naming_Conventions.md` §5.
- No production secrets are ever used locally — local `.env` values are dummy/dev-only credentials pointing at the local Docker services.

## 5. What Local Dev Deliberately Does NOT Match

- No TLS locally (plain HTTP) — production TLS termination is handled at the load balancer (`07_DevOps/Production.md` §3), not something a developer needs to reproduce.
- MinIO instead of a real S3-compatible provider (`07_DevOps/Docker.md` §4).
- A single-node, unscaled Postgres instance instead of the managed/pooled setup in production (`07_DevOps/Production.md` §2).

These gaps are why `07_DevOps/Staging.md` exists as a closer-to-production environment for the checks local dev can't cover.

## 6. Related

- `07_DevOps/Docker.md` — the compose file and Dockerfiles this environment runs
- `08_QA/Test_Strategy.md` — which test layers run locally vs. CI-only
