"""
Shared test helpers for BE-054's RBAC enforcement cutover.

Before BE-054, a bare `CompanyMembership.objects.create(company=..., user=...)`
with no role was sufficient for a test's "member" fixture to pass every
tenant-only permission check. As of BE-054, TenantScopedPermission also
requires the membership's role to hold the specific permission code each
endpoint declares — a role-less membership now has zero codes and gets
403 everywhere. `make_full_access_membership` is the drop-in replacement
for that old pattern in tests that don't care about RBAC granularity and
just need "a member who can do anything in their own company," which is
most of this codebase's pre-BE-054 test suite.

Tests that specifically exercise RBAC (permission-denied cases, specific
role behavior) should build their own narrower Role/RolePermission setup
instead of using this helper.
"""

from apps.users.models import CompanyMembership, CompanyMembershipStatus, Permission, Role, RolePermission
from apps.users.permission_catalog import ALL_PERMISSION_CODES

FULL_ACCESS_ROLE_NAME = "Full Access (Test Fixture)"


def extract_pdf_text(pdf_bytes: bytes) -> str:
    """
    BE-076: PDF-export tests need to assert on a document's actual
    rendered text -- xhtml2pdf/ReportLab compresses the content stream
    (FlateDecode), so naively decoding the raw response bytes only ever
    coincidentally matches uncompressed metadata (e.g. the /Title
    dictionary entry), never the real table/body text. pypdf is a
    test-only dependency (requirements/dev.txt) -- never imported by
    application code.
    """
    import pypdf
    from io import BytesIO

    reader = pypdf.PdfReader(BytesIO(pdf_bytes))
    return "\n".join(page.extract_text() for page in reader.pages)


def make_full_access_role(company) -> Role:
    """
    Get-or-create a per-company Role holding every catalog permission
    code — the test-fixture equivalent of the seeded "Owner" role, but
    independent of it so a test isn't coupled to Owner's exact seeded
    contents changing over time.
    """
    role, created = Role.objects.get_or_create(
        company=company,
        name=FULL_ACCESS_ROLE_NAME,
        defaults={"description": "Test-only role granting every permission code.", "is_active": True},
    )
    if created:
        permissions = Permission.objects.filter(code__in=ALL_PERMISSION_CODES)
        RolePermission.objects.bulk_create(
            [RolePermission(role=role, permission=permission) for permission in permissions]
        )
    return role


def make_full_access_membership(
    company, user, status: str = CompanyMembershipStatus.ACTIVE
) -> CompanyMembership:
    """
    Create a CompanyMembership for `user` in `company` with a role holding
    every permission code, so the membership passes any
    TenantScopedPermission check regardless of which code an endpoint
    requires — the direct replacement for a pre-BE-054 role-less "member"
    fixture.
    """
    role = make_full_access_role(company)
    return CompanyMembership.objects.create(company=company, user=user, role=role, status=status)
