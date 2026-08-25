# CI/CD Pipeline

**Status:** Draft — previously blocked on stack selection; unblocked now that `02_Architecture/Technical_Architecture.md` §2 confirms React/TS/Vite + Django/DRF + PostgreSQL. Assumes GitHub Actions as the CI platform (a reasonable default for a GitHub-hosted repo per `00_Development_Standards/Git_Strategy.md`; swap the concrete YAML for another platform if the team chooses differently — the **stages and gates** below are what matter, not the specific runner).

---

## 1. Pipeline Stages (in order — fail fast)

```
1. Lint & Format Check         (fastest — seconds)
2. Type Check                  (frontend: tsc; backend: mypy, optional)
3. Unit Tests                  (08_QA/Unit_Tests.md)
4. Integration + API Tests     (08_QA/Integration_Tests.md, API_Tests.md — needs Postgres service)
5. Security Scans              (08_QA/Security_Tests.md §5, §7 — dependency, SAST, secrets)
6. Build                        (Docker images per 07_DevOps/Docker.md)
7. Performance Budget Check     (08_QA/Performance_Tests.md — Lighthouse CI, k6 smoke)
8. E2E Tests                    (08_QA/E2E_Tests.md — against a deployed preview, PR-merge/nightly only)
9. Deploy                       (environment-dependent, see §3)
```

Each stage only runs if the prior stage passed — a lint failure never wastes CI minutes running the full test suite.

## 2. Required Gates (non-negotiable, per `00_Development_Standards/Git_Strategy.md` §2)

- **Tenant isolation tests failing = hard merge block, no override.** This is the one gate that can never be skipped or force-merged past, per `08_QA/Integration_Tests.md` §5 and `09_Project/Risk_Register.md` risk #1.
- Any stage 1–5 failure blocks merge.
- A critical/high dependency vulnerability (`08_QA/Security_Tests.md` §5) blocks merge until patched or explicitly triaged with a tracked follow-up.

## 3. Environment-Triggered Deploys

| Trigger | Deploys To | Notes |
|---|---|---|
| PR opened/updated | Ephemeral preview environment (optional, if infra supports it) | Used for E2E tests and manual review |
| Merge to `main` | Staging (`07_DevOps/Staging.md`) | Automatic, no manual approval — staging is meant to always reflect `main` |
| Tag `v*` pushed | Production (`07_DevOps/Production.md`) | Manual approval gate required — production deploys are never fully automatic on a plain merge |

This matches the tagging/release model in `00_Development_Standards/Git_Strategy.md` §5 — `main` is always deployable, but "deployable" and "deployed to production" are deliberately different states.

## 4. Migration Step

`python manage.py migrate` runs as an explicit, isolated deploy step — **before** the new application code is switched to receive traffic in a rolling deploy, and always following the expand/contract pattern from `00_Development_Standards/Git_Strategy.md` §7: a migration must be safe to apply while the *previous* version of the code is still running against the database for the duration of a rolling deploy.

```
Deploy sequence:
  1. Run migrations against production DB
  2. Deploy new application containers (rolling)
  3. Health check new containers
  4. Shift traffic
  5. Terminate old containers
```

## 5. Example Job Skeleton (GitHub Actions)

```yaml
jobs:
  lint:
    runs-on: ubuntu-latest
    steps: [ ... ruff/eslint ... ]

  test-backend:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:16
        env: { POSTGRES_PASSWORD: postgres }
        options: >-
          --health-cmd pg_isready --health-interval 10s
    steps:
      - run: pytest --cov=apps       # unit + integration + API per 08_QA/

  test-frontend:
    runs-on: ubuntu-latest
    steps:
      - run: npm run test            # Vitest unit tests
      - run: npm run build           # also validates the production build compiles

  security-scan:
    runs-on: ubuntu-latest
    steps: [ pip-audit, npm audit, bandit, secrets-scan ]

  e2e:
    needs: [test-backend, test-frontend]
    if: github.event_name == 'push' && github.ref == 'refs/heads/main'
    steps: [ deploy preview, playwright test ]

  deploy-staging:
    needs: [test-backend, test-frontend, security-scan]
    if: github.ref == 'refs/heads/main'
    steps: [ build images, push, migrate, deploy ]

  deploy-production:
    if: startsWith(github.ref, 'refs/tags/v')
    environment: production          # manual approval gate
    steps: [ build images, push, migrate, deploy ]
```

## 6. Rollback

See `07_DevOps/Rollback_Process.md` for what happens when a deploy needs to be reverted — the pipeline above builds the artifact, but rollback is a separate, deliberately simpler operation that doesn't re-run the full pipeline.

## 7. Related

- `00_Development_Standards/Git_Strategy.md` — branch protection rules this pipeline enforces
- `08_QA/Test_Strategy.md` — full detail on each test stage
- `07_DevOps/Monitoring.md` — post-deploy health verification
