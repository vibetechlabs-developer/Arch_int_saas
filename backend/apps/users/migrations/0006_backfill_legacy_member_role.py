"""
BE-054 §1: preserve pre-RBAC-enforcement access for any CompanyMembership
that existed before a role could be assigned to it (BE-050).

For every company that has at least one such membership, ensures a
per-company "Legacy Member" role exists, grants it every catalog
permission code (matching the unrestricted-within-tenant access those
members already had), and assigns it to every one of that company's
null-role memberships.

Explicitly excluded from the backfill: memberships belonging to a
Django-superuser user (`user.is_superuser=True`) — Platform Admin access
is an explicit, separate bypass (05_Security/Tenant.md §6) and must never
be granted through a tenant Role, even incidentally.

Scope note (documented in 05_Security/RBAC_Enforcement_Matrix.md): this
backfills every null-role membership in an affected company regardless of
membership status (active/invited/revoked), not only active ones — an
invited or revoked membership gains no actual access from this (RBAC
resolution already requires status=active), and backfilling it now avoids
a second null-role gap reappearing the moment it's reactivated.

Idempotent: re-running only fills in what's missing (get-or-create role
per company by name, get-or-create each RolePermission grant, and only
reassigns memberships still on role=NULL) — safe to run again after a
partial failure, and a no-op on a database that's already been migrated.
"""

from django.db import migrations

from apps.users.permission_catalog import ALL_PERMISSION_CODES, LEGACY_MEMBER_ROLE_NAME


def backfill_legacy_member_role(apps, schema_editor):
    Company = apps.get_model("company", "Company")
    Role = apps.get_model("users", "Role")
    Permission = apps.get_model("users", "Permission")
    RolePermission = apps.get_model("users", "RolePermission")
    CompanyMembership = apps.get_model("users", "CompanyMembership")

    permissions_by_code = {p.code: p for p in Permission.objects.filter(code__in=ALL_PERMISSION_CODES)}

    affected_company_ids = (
        CompanyMembership.objects.filter(role__isnull=True, deleted_at__isnull=True)
        .exclude(user__is_superuser=True)
        .values_list("company_id", flat=True)
        .distinct()
    )

    for company_id in affected_company_ids:
        company = Company.objects.get(id=company_id)

        role, _ = Role.objects.get_or_create(
            company=company,
            name=LEGACY_MEMBER_ROLE_NAME,
            defaults={
                "description": (
                    "Transitional role auto-created by BE-054's backfill migration to "
                    "preserve the unrestricted-within-tenant access this company's "
                    "pre-existing memberships had before RBAC enforcement. Not intended "
                    "for new members — assign a real role instead."
                ),
                "is_active": True,
            },
        )

        existing_permission_ids = set(
            RolePermission.objects.filter(role=role, deleted_at__isnull=True).values_list(
                "permission_id", flat=True
            )
        )
        RolePermission.objects.bulk_create(
            [
                RolePermission(role=role, permission=permission)
                for permission in permissions_by_code.values()
                if permission.id not in existing_permission_ids
            ]
        )

        CompanyMembership.objects.filter(
            company=company, role__isnull=True, deleted_at__isnull=True
        ).exclude(user__is_superuser=True).update(role=role)


def unbackfill_legacy_member_role(apps, schema_editor):
    """
    Reverse: clear the role back to NULL on every membership currently
    holding a "Legacy Member" role, then remove those roles (and their
    grants, via CASCADE). Does not attempt to distinguish a membership
    this migration itself assigned from one an admin later re-assigned to
    "Legacy Member" by hand — reversing a data migration on a database
    that's since diverged is inherently best-effort.
    """
    Role = apps.get_model("users", "Role")
    CompanyMembership = apps.get_model("users", "CompanyMembership")

    legacy_role_ids = list(Role.objects.filter(name=LEGACY_MEMBER_ROLE_NAME).values_list("id", flat=True))
    CompanyMembership.objects.filter(role_id__in=legacy_role_ids).update(role=None)
    Role.objects.filter(id__in=legacy_role_ids).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0005_seed_permission_catalog"),
    ]

    operations = [
        migrations.RunPython(backfill_legacy_member_role, unbackfill_legacy_member_role),
    ]
