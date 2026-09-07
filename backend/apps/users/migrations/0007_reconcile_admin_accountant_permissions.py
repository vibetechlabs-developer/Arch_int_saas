"""
BE-054 §7: reconcile permission grants on Admin/Accountant roles that were
already seeded (by RoleService.seed_default_roles_for_company, at
company-creation time) before this task's DEFAULT_ROLE_PERMISSIONS
correction landed.

- Admin: grant `company.view`/`company.manage` if not already held —
  these were missing from the original BE-049 seed (an oversight; a
  strictly-enforced Admin couldn't view their own company's profile).
- Accountant / Finance: revoke `expense.create`/`expense.approve` if held
  — these were an undocumented BE-049 extension beyond
  05_Security/Permissions.md §3's literal worked example, removed pending
  explicit product sign-off.

Scoping note: roles are matched by exact name ("Admin" /
"Accountant / Finance"), the same names RoleService.seed_default_roles_for_company
uses — there is no separate "is a default role" flag on Role, so a
company that happens to have hand-created its own custom role under one
of these exact names is reconciled too. This mirrors the same scoping
assumption 0006's Legacy Member backfill makes and is considered an
acceptable, documented risk (see RBAC_Enforcement_Matrix.md).

Idempotent: re-running is a no-op for any role that's already reconciled
(get_or_create for the additions, filter-then-delete — which no-ops on an
empty queryset — for the removals).
"""

from django.db import migrations


ADMIN_ROLE_NAME = "Admin"
ACCOUNTANT_ROLE_NAME = "Accountant / Finance"
ADMIN_CODES_TO_ADD = ["company.view", "company.manage"]
ACCOUNTANT_CODES_TO_REMOVE = ["expense.create", "expense.approve"]


def reconcile_permissions(apps, schema_editor):
    Role = apps.get_model("users", "Role")
    Permission = apps.get_model("users", "Permission")
    RolePermission = apps.get_model("users", "RolePermission")

    admin_permissions = list(Permission.objects.filter(code__in=ADMIN_CODES_TO_ADD))
    for role in Role.objects.filter(name=ADMIN_ROLE_NAME, deleted_at__isnull=True):
        existing_ids = set(
            RolePermission.objects.filter(role=role, deleted_at__isnull=True).values_list(
                "permission_id", flat=True
            )
        )
        RolePermission.objects.bulk_create(
            [
                RolePermission(role=role, permission=permission)
                for permission in admin_permissions
                if permission.id not in existing_ids
            ]
        )

    accountant_permission_ids = set(
        Permission.objects.filter(code__in=ACCOUNTANT_CODES_TO_REMOVE).values_list("id", flat=True)
    )
    for role in Role.objects.filter(name=ACCOUNTANT_ROLE_NAME, deleted_at__isnull=True):
        RolePermission.objects.filter(
            role=role, permission_id__in=accountant_permission_ids, deleted_at__isnull=True
        ).delete()


def reverse_reconcile_permissions(apps, schema_editor):
    """
    Best-effort reverse: re-grant the removed Accountant codes, revoke the
    added Admin codes. Not a perfect inverse if a company had already
    hand-edited these roles independently in the meantime.
    """
    Role = apps.get_model("users", "Role")
    Permission = apps.get_model("users", "Permission")
    RolePermission = apps.get_model("users", "RolePermission")

    admin_permission_ids = set(
        Permission.objects.filter(code__in=ADMIN_CODES_TO_ADD).values_list("id", flat=True)
    )
    for role in Role.objects.filter(name=ADMIN_ROLE_NAME, deleted_at__isnull=True):
        RolePermission.objects.filter(
            role=role, permission_id__in=admin_permission_ids, deleted_at__isnull=True
        ).delete()

    accountant_permissions = list(Permission.objects.filter(code__in=ACCOUNTANT_CODES_TO_REMOVE))
    for role in Role.objects.filter(name=ACCOUNTANT_ROLE_NAME, deleted_at__isnull=True):
        existing_ids = set(
            RolePermission.objects.filter(role=role, deleted_at__isnull=True).values_list(
                "permission_id", flat=True
            )
        )
        RolePermission.objects.bulk_create(
            [
                RolePermission(role=role, permission=permission)
                for permission in accountant_permissions
                if permission.id not in existing_ids
            ]
        )


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0006_backfill_legacy_member_role"),
    ]

    operations = [
        migrations.RunPython(reconcile_permissions, reverse_reconcile_permissions),
    ]
