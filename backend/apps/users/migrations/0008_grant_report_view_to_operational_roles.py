"""
BE-054: found during this task's own role-matrix test pass, not one of
the Backend-Lead-named §7 corrections -- Project Manager, Designer /
Architect, and Sales / CRM User were seeded (BE-049) without `report.view`,
which silently broke the entire point of BE-054 §6's decision to gate the
dashboard with `report.view` (rather than `report.financial_access`)
specifically so these operational roles would keep seeing it. Without this
fix, every one of them got 403 from `GET /reports/dashboard`.

Grants `report.view` to any already-seeded "Project Manager",
"Designer / Architect", or "Sales / CRM User" role that doesn't already
have it. Matched by exact name, same scoping assumption as 0007's
reconciliation. Idempotent (get_or_create-equivalent bulk_create, skipping
roles that already hold the code).
"""

from django.db import migrations


ROLE_NAMES = ["Project Manager", "Designer / Architect", "Sales / CRM User"]
CODE_TO_ADD = "report.view"


def grant_report_view(apps, schema_editor):
    Role = apps.get_model("users", "Role")
    Permission = apps.get_model("users", "Permission")
    RolePermission = apps.get_model("users", "RolePermission")

    try:
        permission = Permission.objects.get(code=CODE_TO_ADD)
    except Permission.DoesNotExist:
        return

    for role in Role.objects.filter(name__in=ROLE_NAMES, deleted_at__isnull=True):
        already_granted = RolePermission.objects.filter(
            role=role, permission=permission, deleted_at__isnull=True
        ).exists()
        if not already_granted:
            RolePermission.objects.create(role=role, permission=permission)


def revoke_report_view(apps, schema_editor):
    Role = apps.get_model("users", "Role")
    Permission = apps.get_model("users", "Permission")
    RolePermission = apps.get_model("users", "RolePermission")

    try:
        permission = Permission.objects.get(code=CODE_TO_ADD)
    except Permission.DoesNotExist:
        return

    for role in Role.objects.filter(name__in=ROLE_NAMES, deleted_at__isnull=True):
        RolePermission.objects.filter(
            role=role, permission=permission, deleted_at__isnull=True
        ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0007_reconcile_admin_accountant_permissions"),
    ]

    operations = [
        migrations.RunPython(grant_report_view, revoke_report_view),
    ]
