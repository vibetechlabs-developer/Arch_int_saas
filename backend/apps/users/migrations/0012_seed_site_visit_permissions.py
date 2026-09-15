"""
BE-062: seed the 5 new `site_visit.*` permission codes introduced by the
Site Visit module, and grant them to any *already-seeded* Admin / Sales
/ CRM User role (RoleService.seed_default_roles_for_company only runs
at company-creation time, so pre-existing companies' default roles
won't pick up new DEFAULT_ROLE_PERMISSIONS codes on their own -- this
mirrors 0011_seed_lead_permissions's exact reconciliation pattern, which
itself mirrors 0007_reconcile_admin_accountant_permissions). New
companies created after this migration get the new codes for free via
the normal seeding path since Permission rows now exist for them.

Idempotent: bulk_create only inserts codes/grants not already present;
re-running is a no-op.
"""

from django.db import migrations

from apps.users.permission_catalog import PERMISSION_CATALOG

SITE_VISIT_CODES = [code for code, module, _action, _description in PERMISSION_CATALOG if module == "site_visit"]
ADMIN_ROLE_NAME = "Admin"
SALES_ROLE_NAME = "Sales / CRM User"
ADMIN_CODES_TO_ADD = ["site_visit.view", "site_visit.create", "site_visit.edit", "site_visit.delete", "site_visit.report"]
SALES_CODES_TO_ADD = ["site_visit.view", "site_visit.create", "site_visit.edit", "site_visit.report"]


def seed_and_grant_site_visit_permissions(apps, schema_editor):
    Permission = apps.get_model("users", "Permission")
    Role = apps.get_model("users", "Role")
    RolePermission = apps.get_model("users", "RolePermission")

    existing_codes = set(Permission.objects.values_list("code", flat=True))
    Permission.objects.bulk_create(
        [
            Permission(code=code, module=module, action=action, description=description)
            for code, module, action, description in PERMISSION_CATALOG
            if module == "site_visit" and code not in existing_codes
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


def unseed_site_visit_permissions(apps, schema_editor):
    Permission = apps.get_model("users", "Permission")
    RolePermission = apps.get_model("users", "RolePermission")

    site_visit_permission_ids = set(
        Permission.objects.filter(code__in=SITE_VISIT_CODES).values_list("id", flat=True)
    )
    RolePermission.objects.filter(permission_id__in=site_visit_permission_ids).delete()
    Permission.objects.filter(code__in=SITE_VISIT_CODES).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0011_seed_lead_permissions"),
    ]

    operations = [
        migrations.RunPython(seed_and_grant_site_visit_permissions, unseed_site_visit_permissions),
    ]
