# Branch Naming Convention

**Priority:** Highest. Companion to `Git_Strategy.md`.

---

## 1. Pattern

```
<type>/<ticket-id>-<short-kebab-case-description>
```

- `<type>` — one of the fixed types in §2.
- `<ticket-id>` — the tracker ID (e.g. `INT-124`) if a tracker is in use; omit only if the team has explicitly decided not to use one, but be consistent project-wide.
- `<short-kebab-case-description>` — 3–6 words, lowercase, hyphenated, describing the change, not the ticket number restated.

## 2. Types

| Type | Use For |
|---|---|
| `feature/` | New functionality (a new module, endpoint, screen) |
| `fix/` | Bug fix on already-shipped behavior |
| `hotfix/` | Urgent production fix, branched from `main`, fast-tracked per `Git_Strategy.md` §6 |
| `refactor/` | Internal restructuring with no behavior change |
| `chore/` | Tooling, dependency bumps, config, non-product-code changes |
| `docs/` | Documentation-only changes (including edits to this `docs/` tree) |
| `test/` | Test-only additions/fixes, no production code change |
| `release/` | Release-prep branches, if ever needed outside the tag-on-main flow |

## 3. Examples

```
feature/INT-142-boq-item-alternate-support
fix/INT-158-invoice-status-not-updating-on-partial-payment
hotfix/INT-201-tenant-scope-bypass-on-expense-list
refactor/INT-133-extract-quotation-versioning-service
chore/INT-110-upgrade-postgres-client
docs/INT-090-update-tenant-isolation-doc
test/INT-175-add-cross-tenant-isolation-suite
```

## 4. Rules

- All lowercase, hyphens only (no underscores, no camelCase, no spaces).
- No personal names or initials in the branch name — branches belong to the work, not the person (git author metadata already tracks who).
- Keep the description short enough to be readable in a CLI branch list (`git branch`) without wrapping — under ~50 characters after the type/ticket prefix.
- Delete the branch immediately after merge (most Git hosts can do this automatically on squash-merge) — stale branches accumulate noise and invite confusion about what's actually in progress.

## 5. Security-Sensitive Branches

Any branch touching `05_Security/` implementation (tenant middleware, permission checks, auth/token logic) should be flagged in its PR description as security-sensitive, regardless of its `feature/`/`fix/` type prefix, to trigger the 2-reviewer rule in `Git_Strategy.md` §2.
