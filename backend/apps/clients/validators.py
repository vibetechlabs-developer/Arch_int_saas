def require_name(name: str) -> str:
    """
    Enforce Client.name is present and non-blank — the model's only
    required field beyond `company` (01_Business/FRS.md §7 lists no other
    mandatory Client field). No format rules for email/mobile/gstin are
    imposed here since none are documented (Database_Schema.md's `client`
    row specifies no CHECK constraints or regex patterns for those columns).

    Consumed by BE-023's create/update serializers/services — BE-022 has
    no request-handling code yet to call this from.
    """
    if not name or not name.strip():
        raise ValueError("Client name cannot be blank or empty.")
    return name.strip()
