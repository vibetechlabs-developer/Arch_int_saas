"""
Seed data for the RBAC Permission catalog and the default per-company roles.

This is a plain data module (no model imports) so it can be safely imported
by both a data migration (apps/users/migrations/0005_seed_permission_catalog.py)
and by RoleService.seed_default_roles_for_company() without either creating a
migration-vs-code-drift risk or a circular import.

05_Security/Permissions.md §7 lists the full canonical per-module permission
code list as an open item pending client sign-off. This catalog is the
Backend Lead's seed of that documented `<module>.<action>` format (§2) and
action vocabulary, scoped to modules that exist in this codebase today — not
a final list. Codes can be added, renamed, or removed later without a model
change, since RolePermission is a plain many-to-many join. No view enforces
these yet (enforcement cutover is BE-054, deliberately deferred).
"""

import re

# (code, module, action, description)
PERMISSION_CATALOG: list[tuple[str, str, str, str]] = [
    ("company.view", "company", "view", "View own company profile."),
    ("company.manage", "company", "manage", "Edit company settings and profile."),
    ("user.view", "user", "view", "View company members."),
    (
        "user.manage",
        "user",
        "manage",
        "Invite, remove, suspend, and assign roles to company members.",
    ),
    ("role.view", "role", "view", "View roles and their permissions."),
    (
        "role.manage",
        "role",
        "manage",
        "Create, edit, delete roles and assign permissions to them.",
    ),
    ("client.view", "client", "view", "View clients."),
    ("client.create", "client", "create", "Create clients."),
    ("client.edit", "client", "edit", "Edit clients."),
    ("client.delete", "client", "delete", "Delete clients."),
    ("lead.view", "lead", "view", "View leads."),
    ("lead.create", "lead", "create", "Create leads."),
    ("lead.edit", "lead", "edit", "Edit leads, transition status, mark lost."),
    ("lead.delete", "lead", "delete", "Delete leads."),
    ("lead.convert", "lead", "convert", "Convert a lead into a client (and optionally a project)."),
    ("project.view", "project", "view", "View projects."),
    ("project.create", "project", "create", "Create projects."),
    ("project.edit", "project", "edit", "Edit project details and status."),
    ("project.delete", "project", "delete", "Delete projects."),
    (
        "project.manage",
        "project",
        "manage",
        "Manage project team members and assignments.",
    ),
    ("product.view", "product", "view", "View the product/work-item catalog."),
    (
        "product.manage",
        "product",
        "manage",
        "Create, edit, delete categories, subcategories, and products.",
    ),
    ("boq.view", "boq", "view", "View a project's BOQ."),
    ("boq.create", "boq", "create", "Create BOQ sections and items."),
    ("boq.edit", "boq", "edit", "Edit BOQ sections and items."),
    ("boq.delete", "boq", "delete", "Delete BOQ sections and items."),
    ("quotation.view", "quotation", "view", "View quotations."),
    ("quotation.create", "quotation", "create", "Create quotations."),
    ("quotation.edit", "quotation", "edit", "Edit draft/unapproved quotations."),
    ("quotation.delete", "quotation", "delete", "Delete quotations."),
    ("quotation.approve", "quotation", "approve", "Approve or reject quotations."),
    ("invoice.view", "invoice", "view", "View invoices."),
    ("invoice.create", "invoice", "create", "Create invoices."),
    ("invoice.edit", "invoice", "edit", "Edit invoices."),
    ("invoice.delete", "invoice", "delete", "Delete/cancel invoices."),
    ("payment.view", "payment", "view", "View payments."),
    ("payment.create", "payment", "create", "Record payments."),
    ("payment.delete", "payment", "delete", "Delete/void payments."),
    ("expense.view", "expense", "view", "View expenses."),
    ("expense.create", "expense", "create", "Submit expenses."),
    ("expense.edit", "expense", "edit", "Edit expenses."),
    ("expense.delete", "expense", "delete", "Delete expenses."),
    (
        "expense.approve",
        "expense",
        "approve",
        "Approve or reject submitted expenses.",
    ),
    ("document.view", "document", "view", "View project documents."),
    ("document.manage", "document", "manage", "Upload and delete project documents."),
    ("audit.view", "audit", "view", "View the company's activity/audit log."),
    (
        "report.view",
        "report",
        "view",
        "View non-financial reports and the dashboard.",
    ),
    (
        "report.financial_access",
        "report",
        "financial_access",
        "View financial figures: revenue, margins, profitability.",
    ),
    ("report.export", "report", "export", "Export report data."),
]

ALL_PERMISSION_CODES: list[str] = [row[0] for row in PERMISSION_CATALOG]

# Legacy Member (BE-054 §1) is deliberately NOT a DEFAULT_ROLE_PERMISSIONS
# entry — it is not auto-seeded for new companies via
# RoleService.seed_default_roles_for_company. It exists only as a one-time
# backfill role, created and granted every catalog code by the BE-054 data
# migration for pre-existing memberships that had no role assigned before
# enforcement began, to preserve their prior (unrestricted-within-tenant)
# access. See RBAC_Enforcement_Matrix.md's "Legacy Member" section — this
# is documented transitional technical debt, not a role a company should
# ever assign to a new member going forward.
LEGACY_MEMBER_ROLE_NAME = "Legacy Member"

# Representative default-role -> permission-code mapping, derived directly
# from 05_Security/Permissions.md §3's role table and worked Accountant
# example. "Site Supervisor" (Phase 4) is deliberately excluded — its
# module (Site Visits, BE-062) has no code yet, so seeding an empty role
# would be a placeholder with no real capability; add it once BE-062 lands.
#
# BE-054 §7 correction: Admin gained `company.view`/`company.manage` (a
# strictly-enforced Admin previously couldn't view/edit their own
# company's profile at all — an oversight, not a deliberate restriction).
# Accountant lost `expense.create`/`expense.approve` (BE-049 had extended
# Accountant beyond `05_Security/Permissions.md` §3's literal worked
# example — "View Expense" only — as a plausible but undocumented
# inference; removed per Backend Lead instruction pending explicit product
# sign-off, so no seeded role currently holds expense.create/approve
# except Owner and the transitional Legacy Member).
DEFAULT_ROLE_PERMISSIONS: dict[str, list[str] | str] = {
    "Owner": "__all__",
    "Admin": [
        "company.view",
        "company.manage",
        "user.view",
        "user.manage",
        "role.view",
        "role.manage",
        "client.view",
        "client.create",
        "client.edit",
        "client.delete",
        "lead.view",
        "lead.create",
        "lead.edit",
        "lead.delete",
        "lead.convert",
        "project.view",
        "project.create",
        "project.edit",
        "project.delete",
        "project.manage",
        "product.view",
        "product.manage",
        "document.view",
        "document.manage",
        "audit.view",
        "report.view",
    ],
    "Project Manager": [
        "project.view",
        "project.edit",
        "project.manage",
        "client.view",
        "boq.view",
        "quotation.view",
        "document.view",
        "document.manage",
        # BE-054 §6 consequence: the dashboard is gated with report.view
        # (not financial_access) specifically to preserve operational
        # dashboard access for roles like this one — that only actually
        # works if the role holds report.view. Found and fixed during
        # BE-054's own role-matrix test pass (RBAC_Enforcement_Matrix.md).
        "report.view",
    ],
    "Designer / Architect": [
        "project.view",
        "boq.view",
        "quotation.view",
        "document.view",
        "document.manage",
        "report.view",
    ],
    "Accountant / Finance": [
        "client.view",
        "project.view",
        "boq.view",
        "quotation.view",
        "quotation.create",
        "quotation.edit",
        "quotation.approve",
        "invoice.view",
        "invoice.create",
        "invoice.edit",
        "invoice.delete",
        "payment.view",
        "payment.create",
        "payment.delete",
        "expense.view",
        "expense.edit",
        "report.view",
        "report.financial_access",
        "report.export",
    ],
    "Sales / CRM User": [
        "client.view",
        "client.create",
        "client.edit",
        "lead.view",
        "lead.create",
        "lead.edit",
        "lead.convert",
        "project.view",
        "boq.view",
        "quotation.view",
        "quotation.create",
        "report.view",
    ],
}


def _slugify_system_key(name: str) -> str:
    """
    Deterministic `Role.system_key` derivation from a documented default
    role's display name -- used ONLY at seed time
    (RoleService.seed_default_roles_for_company) and, for historical
    backfill, only against the exact names above. Never re-derived from a
    role's *current* display name afterward (renaming a role never
    changes its system_key), and never run against a customer-created
    role regardless of what that role happens to be named (BE-069).
    """
    return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")


#: The one default role with dedicated protection (undeletable; a company
#: must always keep at least one ACTIVE membership holding it) -- see
#: apps.users.models.Role.system_key and apps.users.services.
#: CompanyMembershipService's last-owner invariant. Every other default
#: role also gets a stable system_key (identity, not protection).
OWNER_SYSTEM_KEY: str = _slugify_system_key("Owner")

#: role display name -> stable system_key, for every documented default
#: role. Consulted only by the seeding path and by the one-time historical
#: backfill migration -- never by request-time authorization logic, which
#: must always compare against `Role.system_key` on the actual row, never
#: recompute this mapping from a role's current (possibly renamed) name.
DEFAULT_ROLE_SYSTEM_KEYS: dict[str, str] = {
    role_name: _slugify_system_key(role_name) for role_name in DEFAULT_ROLE_PERMISSIONS
}
