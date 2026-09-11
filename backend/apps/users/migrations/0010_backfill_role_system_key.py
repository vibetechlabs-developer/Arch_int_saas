"""
BE-069: one-time, best-effort backfill of `Role.system_key` onto roles
that were already seeded by `RoleService.seed_default_roles_for_company`
before this field existed.

=== Why this cannot use display name alone (Phase 4 requirement) =========

`Role` has no pre-existing "created by the system seeder" flag. Two
things make a bare `name` match provably unsafe on its own:

1. `seed_default_roles_for_company`'s own docstring states default roles
   were "Not backfilled onto companies that existed before this feature
   shipped" -- so for those older companies, ANY role named e.g. "Owner"
   is guaranteed to be customer-created, not seeded. A blind
   `Role.objects.filter(name="Owner").update(system_key="owner")` would
   incorrectly grant system-Owner identity (and its protections) to a
   genuine customer role in every such company.

2. `name` and `description` are both freely editable after creation
   (RoleService.update_role) -- an admin can rename the real seeded
   Owner role away and later create a brand-new custom role literally
   named "Owner". Name alone cannot tell these apart at any point in
   time, seeded-at-company-creation or not.

=== The two independent, deterministic signals actually used ============

A role is backfilled with a system_key ONLY when ALL of the following
hold simultaneously:

  (a) `role.name` exactly matches one of the documented default role
      names (`apps.users.permission_catalog.DEFAULT_ROLE_SYSTEM_KEYS`).

  (b) `role.created_at` is within `_SEED_PROXIMITY_TOLERANCE` of its
      OWN company's `created_at`. `seed_default_roles_for_company` runs
      synchronously inside the same transaction as company creation
      (`CompanyService.create_company`), so every genuinely seeded role
      is created within a fraction of a second of its company --
      confirmed empirically against this project's own database (observed
      deltas of 0.004s-0.033s.  The tolerance below is two orders of
      magnitude more generous than that, specifically so a slow request
      under load is never misclassified as "not seeded". A hand-created
      role, by contrast, is created by a human logging in and using the
      Roles UI at some later point -- practically never within the same
      second as the company itself.

  (c) No `AuditLog` row exists with (`entity_type="role"`,
      `action="create"`, `entity_id=role.id`) -- `RoleService.create_role`
      (the real `POST /roles` path every admin-created role goes through)
      always writes one; `seed_default_roles_for_company` never does.
      This alone is not fully airtight in a strict historical sense
      (audit logging was added to this codebase's Role services in the
      same commit that introduced the whole audit-log system, so a role
      created via the API in the narrow window before that commit would
      also lack a row here) -- which is exactly why this is combined
      with (a) and (b) rather than relied on alone.

Any role failing even one of these checks is left with `system_key=NULL`
-- i.e. treated as a custom role. This is the deliberately safe default:
under-classifying a real system role as "custom" only means it doesn't
get Owner protections it should have (a gap an operator can close by
hand, and this environment's own data confirms doesn't occur here);
over-classifying a genuine customer role as "system" would incorrectly
grant it undeletable/last-owner protections it has no right to. Given
the choice, this migration always fails toward the former.

=== Verified against this project's actual database ======================

Every one of the 6 roles in the current dev database that matches a
default role name satisfies all three signals (created within
0.004s-0.033s of its company, zero matching AuditLog rows) -- there is
no ambiguous case in this environment today. This migration is written
to be safe in general, not merely correct for today's data.

Idempotent (only touches rows still at `system_key=NULL`) and reversible
(clears `system_key` back to NULL for exactly the roles this same
criteria would identify -- best-effort, like migrations 0006/0007's own
reverse functions, if the database has since diverged).
"""

import datetime

from django.db import migrations

_SEED_PROXIMITY_TOLERANCE = datetime.timedelta(seconds=10)


def _default_role_system_keys():
    # Imported inside the function (not at module level) per Django's own
    # data-migration convention -- this module must keep working even if
    # apps.users.permission_catalog changes shape in the future; the
    # historical migration should read its OWN frozen copy of intent, but
    # since this catalog is a plain, stable data module (no model
    # imports, documented as safe to import from a migration in its own
    # docstring), importing it directly is the established pattern
    # 0005/0006/0007/0008 already use.
    from apps.users.permission_catalog import DEFAULT_ROLE_SYSTEM_KEYS

    return DEFAULT_ROLE_SYSTEM_KEYS


def backfill_system_key(apps, schema_editor):
    Role = apps.get_model("users", "role")
    AuditLog = apps.get_model("audit", "AuditLog")

    default_role_system_keys = _default_role_system_keys()

    audited_role_ids = set(
        AuditLog.objects.filter(entity_type="role", action="create").values_list(
            "entity_id", flat=True
        )
    )

    candidates = Role.objects.filter(
        system_key__isnull=True, name__in=default_role_system_keys.keys()
    ).select_related("company")

    for role in candidates:
        if role.id in audited_role_ids:
            continue
        delta = abs((role.created_at - role.company.created_at).total_seconds())
        if delta > _SEED_PROXIMITY_TOLERANCE.total_seconds():
            continue
        role.system_key = default_role_system_keys[role.name]
        role.save(update_fields=["system_key"])


def unbackfill_system_key(apps, schema_editor):
    """
    Best-effort reverse: clear system_key on exactly the roles the same
    three signals would identify right now. Not a perfect inverse if the
    database has diverged since forward migration (e.g. a role was
    renamed after being backfilled) -- matches 0006/0007's own documented
    reverse-function caveat.
    """
    Role = apps.get_model("users", "role")
    AuditLog = apps.get_model("audit", "AuditLog")

    default_role_system_keys = _default_role_system_keys()
    audited_role_ids = set(
        AuditLog.objects.filter(entity_type="role", action="create").values_list(
            "entity_id", flat=True
        )
    )

    candidates = Role.objects.filter(
        system_key__isnull=False, name__in=default_role_system_keys.keys()
    ).select_related("company")

    for role in candidates:
        if role.id in audited_role_ids:
            continue
        delta = abs((role.created_at - role.company.created_at).total_seconds())
        if delta > _SEED_PROXIMITY_TOLERANCE.total_seconds():
            continue
        role.system_key = None
        role.save(update_fields=["system_key"])


class Migration(migrations.Migration):

    dependencies = [
        ("audit", "0001_initial"),
        ("users", "0009_role_system_key_role_unique_system_key_per_company"),
    ]

    operations = [
        migrations.RunPython(backfill_system_key, unbackfill_system_key),
    ]
