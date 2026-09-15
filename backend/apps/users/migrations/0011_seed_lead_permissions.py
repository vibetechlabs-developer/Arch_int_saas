"""
BE-061: seed the 5 new `lead.*` permission codes introduced by the
Leads/CRM module, and grant them to any *already-seeded* Admin / Sales /
CRM User role (RoleService.seed_default_roles_for_company only runs at
company-creation time, so pre-existing companies' default roles won't
pick up new DEFAULT_ROLE_PERMISSIONS codes on their own -- this mirrors
0007_reconcile_admin_accountant_permissions's exact reconciliation
pattern). New companies created after this migration get the new codes
for free via the normal seeding path since Permission rows now exist for
them.

Idempotent: bulk_create only inserts codes/grants not already present;
re-running is a no-op.
"""

from django.db import migrations

from apps.users.permission_catalog import PERMISSION_CATALOG

LEAD_CODES = [code for code, module, _action, _description in PERMISSION_CATALOG if module == "lead"]
ADMIN_ROLE_NAME = "Admin"
SALES_ROLE_NAME = "Sales / CRM User"
ADMIN_CODES_TO_ADD = ["lead.view", "lead.create", "lead.edit", "lead.delete", "lead.convert"]
SALES_CODES_TO_ADD = ["lead.view", "lead.create", "lead.edit", "lead.convert"]


def seed_and_grant_lead_permissions(apps, schema_editor):
    Permission = apps.get_model("users", "Permission")
    Role = apps.get_model("users", "Role")
    RolePermission = apps.get_model("users", "RolePermission")

    existing_codes = set(Permission.objects.values_list("code", flat=True))
    Permission.objects.bulk_create(
        [
            Permission(code=code, module=module, action=action, description=description)
            for code, module, action, description in PERMISSION_CATALOG
            if module == "lead" and code not in existing_codes
        ]
    )

    def grant(role_name: str, codes: list[str]) -> None:
        permissions = list(Permission.objects.filter(code__in=codes))
        for role in Role.objects.filter(name=role_name, deleted_at__isnull=True):
            existing_ids = set(
                RolePermission.objects.filter(role=role, deleted_at__isnull=True).values_list(
                    "permission_id", flat=True
                )
            )
            RolePermission.objects.bulk_create(
                [
                    RolePermission(role=role, permission=permission)
                    for permission in permissions
                    if permission.id not in existing_ids
                ]
            )

    grant(ADMIN_ROLE_NAME, ADMIN_CODES_TO_ADD)
    grant(SALES_ROLE_NAME, SALES_CODES_TO_ADD)


def unseed_lead_permissions(apps, schema_editor):
    Permission = apps.get_model("users", "Permission")
    RolePermission = apps.get_model("users", "RolePermission")

    lead_permission_ids = set(
        Permission.objects.filter(code__in=LEAD_CODES).values_list("id", flat=True)
    )
    RolePermission.objects.filter(permission_id__in=lead_permission_ids).delete()
    Permission.objects.filter(code__in=LEAD_CODES).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0010_backfill_role_system_key"),
    ]

    operations = [
        migrations.RunPython(seed_and_grant_lead_permissions, unseed_lead_permissions),
    ]
