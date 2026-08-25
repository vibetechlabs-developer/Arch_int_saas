# Commit Message Format

**Priority:** Highest. Based on [Conventional Commits](https://www.conventionalcommits.org/), adapted to this project's module vocabulary.

---

## 1. Format

```
<type>(<scope>): <subject>

<body — optional>

<footer — optional>
```

- **type** — one of the types in §2.
- **scope** — the business module affected, matching `Folder_Structure.md` module names: `client`, `project`, `boq`, `quotation`, `invoice`, `payment`, `expense`, `report`, `auth`, `user`, `role-permission`, `company`, `platform`, etc. Use `*` only for truly cross-cutting changes.
- **subject** — imperative mood, lowercase, no trailing period, under ~72 characters: "add", not "added"/"adds".
- **body** — the *why*, not a restatement of the diff; wrap at ~72 chars; blank line before it.
- **footer** — ticket reference (`Refs: INT-142`), breaking-change notice, or co-author lines.

## 2. Types

| Type | Use For |
|---|---|
| `feat` | New feature/functionality |
| `fix` | Bug fix |
| `refactor` | Code change that neither fixes a bug nor adds a feature |
| `perf` | Performance improvement |
| `test` | Adding/correcting tests |
| `docs` | Documentation only |
| `chore` | Tooling, deps, build config |
| `style` | Formatting only, no logic change |
| `ci` | CI/CD pipeline changes |
| `revert` | Reverts a previous commit |

## 3. Examples

```
feat(quotation): add versioning on revision

Each revision now creates a new quotation row referencing the
previous version instead of mutating the sent quotation, per the
source requirement that quotations must be versioned.

Refs: INT-142
```

```
fix(invoice): recompute status after partial payment void

Voiding a payment left the invoice status at "Paid" even when the
remaining paid amount no longer covered the total.

Refs: INT-158
```

```
fix(security): enforce company_id check on expense repository

Expense list query was missing the company_id filter, allowing
cross-tenant reads by ID. Added the mandatory filter and a
regression test per 08_QA/Test_Cases.md §1.

BREAKING CHANGE: none
Refs: INT-201
```

```
chore(deps): bump postgres client to 8.x
```

## 4. Rules

- One logical change per commit. A commit that mixes a bug fix with an unrelated refactor should be split.
- Never commit with a message like `"fix"`, `"wip"`, `"updates"`, or `"asdf"` — even on a feature branch, since squash-merge (per `Git_Strategy.md` §4) will surface the PR title, but reviewers still read the commit-by-commit history during review.
- **Breaking changes** (API contract or non-backward-compatible schema change) must include a `BREAKING CHANGE:` footer line describing the impact, even if the value is "none" is not applicable — omit the line entirely if there is no breaking change, don't write "none."
- Security fixes (anything under `05_Security/` implementation, or a tenant-isolation bug like the example above) must reference the relevant test category added in `08_QA/Test_Cases.md`.

## 5. PR Title = Squash Commit Message

Since `Git_Strategy.md` §4 squash-merges every PR, the **PR title** becomes the final commit message on `main` — write PR titles in this same `<type>(<scope>): <subject>` format from the start, not as a separate "descriptive sentence" style.
