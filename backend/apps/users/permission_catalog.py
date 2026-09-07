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

# Representative default-role -> permission-code mapping, derived directly
# from 05_Security/Permissions.md §3's role table and worked Accountant
# example. "Site Supervisor" (Phase 4) is deliberately excluded — its
# module (Site Visits, BE-062) has no code yet, so seeding an empty role
# would be a placeholder with no real capability; add it once BE-062 lands.
DEFAULT_ROLE_PERMISSIONS: dict[str, list[str] | str] = {
    "Owner": "__all__",
    "Admin": [
        "user.view",
        "user.manage",
        "role.view",
        "role.manage",
        "client.view",
        "client.create",
        "client.edit",
        "client.delete",
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
    ],
    "Designer / Architect": [
        "project.view",
        "boq.view",
        "quotation.view",
        "document.view",
        "document.manage",
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
        "expense.create",
        "expense.edit",
        "expense.approve",
        "report.view",
        "report.financial_access",
        "report.export",
    ],
    "Sales / CRM User": [
        "client.view",
        "client.create",
        "client.edit",
        "project.view",
        "boq.view",
        "quotation.view",
        "quotation.create",
    ],
}
