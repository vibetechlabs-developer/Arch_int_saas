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
