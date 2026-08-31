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
