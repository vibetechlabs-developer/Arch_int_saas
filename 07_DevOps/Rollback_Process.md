# Rollback Process

**Status:** Draft.

---

## 1. Principle

A rollback reverts the **running application code** to a previously known-good state, quickly, without re-running the full CI pipeline (`07_DevOps/CI_CD.md`) and — critically — **without assuming the database can be rolled back the same way**. Application rollback and database rollback are different operations with very different risk profiles; conflating them is the most common way a rollback makes an incident worse instead of better.

## 2. Application Rollback (the common case)

Because every production deploy is tagged (`00_Development_Standards/Git_Strategy.md` §5), rolling back the application is:

```
1. Identify the last known-good tag (e.g. v1.4.2, before the problematic v1.4.3)
2. Re-deploy the container images already built for that tag — do NOT rebuild from source,
   use the exact artifact that was already verified in CI/staging for that tag
3. Health-check the redeployed containers
4. Shift traffic back
```

This should be executable within minutes, as a manual-trigger deploy job, not a novel process invented during an incident.

## 3. The Migration Problem

**A migration that has already run in production cannot always be safely un-run**, especially once new rows have been written under the new schema. This is why `00_Development_Standards/Git_Strategy.md` §7 and `07_DevOps/CI_CD.md` §4 require the expand/contract pattern: every migration must be written so that the *previous* application version keeps working against the *new* schema for at least one deploy cycle.

Consequence for rollback:
- **Rolling back application code alone (§2), leaving the newer schema in place, is the default and preferred rollback path** — it works precisely because migrations are required to be backward-compatible.
- **Rolling back the database schema itself is a last resort**, used only when a migration is discovered to be actively harmful (e.g. silently corrupting data) and never attempted without first taking a fresh backup (`07_DevOps/Backup_Strategy.md`) and ideally testing the reverse migration in staging first — not run directly against production under incident pressure.

## 4. Decision Flow

```
Incident detected (07_DevOps/Monitoring.md alert, or manual report)
   ↓
Is the problem caused by application code (not schema)?
   ├─ Yes → Application rollback (§2) — fast, low-risk, do this first
   └─ No / unclear → Investigate before acting; a schema rollback attempted
                       under uncertainty risks compounding the incident
```

**When in doubt, roll back the application first** — it's reversible and low-risk. Only escalate to touching the database schema once the application-only rollback has been tried and the problem persists, confirming it's genuinely a data/schema issue.

## 5. Feature Flags as a Rollback Alternative

Where a specific feature (not the whole deploy) is the problem, disabling it via a feature flag (`01_Business/FRS.md` §1 Platform's "Feature Flags," Phase 5 per `09_Project/Roadmap.md` — but worth introducing earlier for exactly this operational reason, not only as a Phase 5 product feature) is often faster and safer than a full application rollback, since it doesn't affect any other code shipped in the same release.

## 6. Post-Rollback

Every rollback triggers:
- An incident note (what broke, what was rolled back to, timestamp) — feeds into the eventual root-cause writeup.
- A hotfix branch (`00_Development_Standards/Branch_Naming.md`, `Git_Strategy.md` §6) to actually fix the problem before re-attempting the deploy — a rollback resolves the immediate incident, it doesn't fix the underlying bug.
- A review of whether the CI gates in `07_DevOps/CI_CD.md` §2 should have caught this before it reached production, and if not, what test (`08_QA/Test_Strategy.md`) should be added.

## 7. Related

- `07_DevOps/CI_CD.md` §4 — the deploy sequence this reverses
- `07_DevOps/Backup_Strategy.md` — for the rare case that actually requires data restoration, not just application rollback
- `00_Development_Standards/Git_Strategy.md` §6 — hotfix process for the actual fix that follows a rollback
