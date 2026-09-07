from typing import Any, Dict, Optional

# Per-entity-type allowlist of fields permitted in before_state/after_state.
# This is a defense-in-depth safety net, not the only line of defense —
# callers should already only pass the fields relevant to the change — but
# an audit_log row is durable and never-expired (Logging_Standards.md §5),
# so a secret leaked here can't be pruned/rotated away like a normal log
# line. Anything not explicitly listed is silently dropped, never persisted.
ENTITY_FIELD_ALLOWLISTS: Dict[str, set] = {
    "role": {"name", "description", "is_active"},
    "company": {"name", "status", "currency", "gst_number", "settings"},
    # Authentication events (login/logout/refresh/password reset) audit the
    # "user" entity. Deliberately excludes password/password_hash/token
    # fields entirely — only a non-sensitive identifier is ever persisted.
    "user": {"email"},
    # Deliberate MVP payload scope, not a permanent product rule (BE-023):
    # `addresses`/`notes` are excluded for now as a privacy/payload-size
    # choice, since they're free-form/structured content rather than
    # simple identifiers — can be added later if audit review needs them.
    "client": {"name", "company_name", "email", "mobile", "gstin"},
    # BE-029: full field coverage (no free-text/privacy-sensitive fields
    # exist on Project the way client.addresses/notes do). FK ids
    # (client_id/assigned_to_id) and date/datetime values are stringified
    # by apps.projects.services._audit_state before reaching here — plain
    # json.JSONEncoder (this JSONField has no custom encoder) can't
    # serialize a raw uuid.UUID/date/datetime.
    "project": {
        "name",
        "client_id",
        "status",
        "priority",
        "assigned_to_id",
        "start_date",
        "deadline",
        "follow_up_reminder_at",
    },
    # Team membership changes are their own entity (their own entity_id),
    # not folded into "project" rows — project_id/user_id/assigned_by_id
    # are carried in the state itself so a row is self-describing without
    # a join, matching how every other audited entity's state is a
    # snapshot of its own fields.
    "project_member": {"project_id", "user_id", "assigned_by_id"},
    # BE-031: Category has exactly one field beyond company/id.
    "product_category": {"name"},
    # BE-032: category_id is stringified by
    # apps.products.services._subcategory_audit_state before reaching
    # here (same reasoning as Project's FK ids — this JSONField has no
    # custom encoder and can't serialize a raw uuid.UUID).
    "product_subcategory": {"name", "category_id"},
    # BE-033: subcategory_id and the Decimal money/percentage fields are
    # stringified by apps.products.services._product_audit_state before
    # reaching here — same JSONField-has-no-custom-encoder reasoning as
    # Project's FK ids (BE-029).
    "product": {
        "name",
        "subcategory_id",
        "image_url",
        "unit",
        "default_cost",
        "default_selling_rate",
        "tax_rate",
        "status",
    },
    # BE-035: BOQ is only ever audited at creation (auto-created on first
    # access, not user-editable) -- project_id is the one field worth
    # recording.
    "boq": {"project_id"},
    "boq_section": {"name", "sort_order"},
    # BE-036: product_id and the Decimal fields are stringified by
    # apps.boq.services._item_audit_state before reaching here -- same
    # JSONField-has-no-custom-encoder reasoning as Project (BE-029) and
    # Product (BE-033).
    "boq_item": {
        "product_id",
        "description",
        "quantity",
        "unit",
        "rate",
        "discount",
        "tax",
        "amount",
        "is_optional",
        "is_alternative",
        "notes",
    },
    # BE-039: full field coverage. project_id/boq_id/client_id (UUIDs),
    # subtotal/discount/tax/total (Decimal), and valid_until (a plain
    # datetime.date -- a new type prior audit helpers didn't need to
    # handle) are all stringified by
    # apps.quotations.services._serialize_quotation_audit_value before
    # reaching here -- same JSONField-has-no-custom-encoder reasoning as
    # Project (BE-029), Product (BE-033), and BOQItem (BE-036).
    "quotation": {
        "project_id",
        "boq_id",
        "client_id",
        "quote_number",
        "version",
        "subtotal",
        "discount",
        "tax",
        "total",
        "terms",
        "payment_schedule",
        "valid_until",
        "status",
        "notes",
    },
    # BE-042: project_id/quotation_id/client_id (UUIDs), the Decimal money
    # fields, and due_date (a plain datetime.date) are all stringified by
    # apps.invoices.services._serialize_invoice_audit_value before
    # reaching here -- same JSONField-has-no-custom-encoder reasoning as
    # Quotation (BE-039). Note `status` here is always the persisted base
    # value (draft/sent/partially_paid/paid/cancelled) -- "overdue" is a
    # read-time-only derivation (InvoiceService.compute_effective_status)
    # that never reaches the audit log.
    "invoice": {
        "project_id",
        "quotation_id",
        "client_id",
        "invoice_number",
        "subtotal",
        "discount",
        "tax",
        "total",
        "due_date",
        "payment_terms",
        "status",
        "notes",
    },
    # BE-043: invoice_id/client_id/project_id (UUIDs), amount (Decimal),
    # and payment_date (a plain datetime.date) are all stringified by
    # apps.payments.services._serialize_payment_audit_value before
    # reaching here -- same JSONField-has-no-custom-encoder reasoning as
    # Invoice (BE-042).
    "payment": {
        "invoice_id",
        "client_id",
        "project_id",
        "payment_date",
        "amount",
        "method",
        "reference_number",
        "receipt_url",
        "notes",
    },
    # BE-044: project_id/employee_id/added_by_id (UUIDs), amount/tax
    # (Decimal), and date (a plain datetime.date) are all stringified by
    # apps.expenses.services._serialize_expense_audit_value before
    # reaching here -- same JSONField-has-no-custom-encoder reasoning as
    # Payment (BE-043).
    "expense": {
        "project_id",
        "category",
        "vendor",
        "employee_id",
        "amount",
        "tax",
        "date",
        "payment_method",
        "receipt_url",
        "notes",
        "added_by_id",
        "approval_status",
    },
    # BE-046: project_id/entity_id/uploaded_by_id (UUIDs) are stringified
    # by apps.documents.services._serialize_document_audit_value before
    # reaching here -- same JSONField-has-no-custom-encoder reasoning as
    # every prior sprint's audit helper.
    "document": {
        "project_id",
        "entity_type",
        "entity_id",
        "file_url",
        "version",
        "uploaded_by_id",
    },
    # BE-052: user_id/role_id are stringified by
    # apps.users.services.CompanyMembershipService._membership_snapshot
    # before reaching here -- same JSONField-has-no-custom-encoder
    # reasoning as every prior sprint's audit helper. Never includes the
    # invited email as free text beyond what's already resolvable via
    # user_id, keeping this row self-describing without duplicating PII.
    "company_membership": {"user_id", "role_id", "status"},
    # BE-049/BE-051: only the resulting permission-code set is recorded,
    # never full Permission objects (a code is not sensitive).
    "role_permission": {"permission_codes"},
}


def filter_state_fields(entity_type: str, state: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """
    Filter a before/after state dict down to the allowlisted fields for the
    given entity_type. Returns None unchanged (create has no before_state,
    delete has no after_state). An entity_type with no registered allowlist
    yields an empty dict rather than raising, so a caller can't accidentally
    persist an unreviewed field set by forgetting to register one — but this
    should be treated as a bug to fix (add the allowlist), not relied on.
    """
    if state is None:
        return None

    allowlist = ENTITY_FIELD_ALLOWLISTS.get(entity_type, set())
    return {key: value for key, value in state.items() if key in allowlist}
