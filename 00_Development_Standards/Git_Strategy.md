# Git Strategy

**Priority:** Highest.

---

## 1. Model: Trunk-Based Development with Short-Lived Feature Branches

- `main` is always deployable and always protected — no direct pushes, ever, including from admins.
- All work happens on short-lived branches created from `main` (see `Branch_Naming.md`) and merged back via Pull Request.
- Branches should live **days, not weeks**. If a feature is too large for that, split it behind a feature flag or into smaller incremental PRs rather than keeping a long-lived branch that drifts from `main`.

This model is chosen over Git Flow because the project is a SaaS product with continuous deployment goals, not a shrink-wrapped product with parallel maintained release lines — Git Flow's `develop`/`release`/`hotfix` branch overhead isn't justified here.

## 2. Branch Protection Rules (on `main`)

- Require at least 1 approving review before merge (2 for changes touching `05_Security/` implementation code — tenant isolation, auth, permissions).
- Require the full CI pipeline (lint, type-check, tests, build) to pass — see `07_DevOps/CI_CD.md`.
- Require branches to be up to date with `main` before merge (rebase or merge `main` in).
- No force-push to `main`.
- Squash-merge only (see §4).

## 3. Pull Request Workflow

1. Branch created from latest `main`.
2. Work committed in small, logical commits (see `Commit_Message_Format.md`).
3. PR opened as soon as there's reviewable work — draft PRs encouraged for early feedback, not just at "done."
4. PR description includes: what changed, why, and how it was tested (link to `08_QA/Test_Cases.md` categories touched, if applicable).
5. Reviewer runs through `Code_Review_Checklist.md`.
6. Author addresses feedback via new commits (don't force-push mid-review — it breaks the reviewer's incremental diff view); squash happens automatically at merge.
7. Once approved and CI green, squash-merge into `main`.

## 4. Merge Strategy: Squash Merge

Every PR becomes exactly one commit on `main`, using the PR title as the commit message (formatted per `Commit_Message_Format.md`). This keeps `main`'s history readable as one line per feature/fix, while the PR itself retains the full commit-by-commit history for review context.

## 5. Releases & Tagging

- Tag `main` at each production deployment: `v<major>.<minor>.<patch>` (Semantic Versioning).
- **Major:** breaking API contract change (see `04_API/` versioning notes) or breaking DB migration requiring coordinated rollout.
- **Minor:** new feature/module (e.g. a new Phase from `09_Project/Roadmap.md` ships).
- **Patch:** bug fix, no new functionality.
- Tags are the source of truth for "what's in production" — not branch names.

## 6. Hotfixes

For a production-breaking bug that can't wait for the normal PR cycle:
1. Branch from `main` as `hotfix/<ticket>-<description>` (see `Branch_Naming.md`).
2. Same PR/review/CI requirements apply — **never skip review or CI to move faster**, since a bad hotfix on a multi-tenant system risks every company at once.
3. Merge to `main`, tag, deploy.

## 7. Migrations

Database migrations (`03_Database/`) are committed alongside the code that depends on them, in the same PR — never as a separate, later PR. A migration must be backward-compatible with the currently-deployed code for at least one deploy cycle (expand/contract pattern) if the deployment isn't atomic across DB and app.

## 8. What Must Never Happen

- No committing directly to `main`.
- No `git push --force` to any shared branch (feature branches you alone own are fine to force-push after a rebase; anything another person has pulled is not).
- No merging with failing CI, "just this once."
- No committing secrets, `.env` files, or credentials — see `.gitignore` requirements in `07_DevOps/`.
- No rewriting merged history on `main`.

## 9. Related

- `Branch_Naming.md`, `Commit_Message_Format.md`, `Code_Review_Checklist.md`
- `07_DevOps/CI_CD.md` for what the pipeline actually runs
