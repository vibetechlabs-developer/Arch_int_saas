from django.db import migrations

from apps.users.permission_catalog import PERMISSION_CATALOG


def seed_permissions(apps, schema_editor):
    Permission = apps.get_model("users", "Permission")
    existing_codes = set(Permission.objects.values_list("code", flat=True))

    Permission.objects.bulk_create(
        [
            Permission(code=code, module=module, action=action, description=description)
            for code, module, action, description in PERMISSION_CATALOG
            if code not in existing_codes
        ]
    )


def unseed_permissions(apps, schema_editor):
    Permission = apps.get_model("users", "Permission")
    seeded_codes = [row[0] for row in PERMISSION_CATALOG]
    Permission.objects.filter(code__in=seeded_codes).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0004_permission_companymembership_role_rolepermission"),
    ]

    operations = [
        migrations.RunPython(seed_permissions, unseed_permissions),
    ]
