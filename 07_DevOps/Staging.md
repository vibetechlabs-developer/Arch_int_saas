# Staging Environment

**Status:** Draft.

---

## 1. Purpose

Staging is the environment that mirrors production configuration as closely as practical, used for: E2E tests against a real deployment (`08_QA/E2E_Tests.md`), pre-release performance/security checks (`08_QA/Performance_Tests.md`, `08_QA/Security_Tests.md`), and client UAT walkthroughs (`08_QA/UAT.md`'s checklist explicitly requires "deployed to a UAT/staging environment matching production configuration" as a pre-condition).

## 2. Deployment

Per `07_DevOps/CI_CD.md` §3: every merge to `main` deploys to staging automatically, no manual approval — staging is meant to always reflect the current state of `main`, so it's a reliable target for "what will ship next," not a separately-managed environment that can drift.

## 3. What Mirrors Production

- Same container images (built from the same `07_DevOps/Docker.md` production targets, not the dev targets).
- Same Django settings module class (production-mode settings — `DEBUG=False`, real security headers) with staging-specific values (its own database, its own object storage bucket/prefix).
- Same migration process (`07_DevOps/CI_CD.md` §4).

## 4. What Differs From Production

- **Data:** seeded/synthetic or anonymized data only — staging never contains real client PII or real financial records copied from production. If production data is ever needed to reproduce a bug, it is anonymized/scrubbed before loading into staging, not copied as-is.
- **Scale:** staging runs at a smaller instance/replica count than production — enough to be representative for performance budget checks (`08_QA/Performance_Tests.md`), not necessarily full production capacity.
- **External integrations:** third-party services (email, WhatsApp — Phase 5) are pointed at sandbox/test credentials in staging, never live production accounts.

## 5. Access

Staging is reachable by the internal team and by the client for UAT sessions (`08_QA/UAT.md`), but is not publicly indexed/discoverable — basic access control (e.g. a shared auth gate in front of the whole environment, in addition to the app's own login) is appropriate given it may contain the client's own real-shaped test data during UAT sessions.

## 6. Reset Cadence

Staging data is periodically reset to a clean seeded state (e.g. before each major UAT round) so accumulated test artifacts from prior QA/UAT sessions don't confuse the next round — document the reset command/process here once the seed tooling from `07_DevOps/Development_Environment.md` §2 is extended to a staging-safe variant.

## 7. Related

- `07_DevOps/Production.md` — the environment staging mirrors
- `08_QA/UAT.md` — the primary business use of this environment
