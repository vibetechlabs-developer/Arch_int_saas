def require_name(name: str) -> str:
    """
    Enforce Lead.name is present and non-blank — the model's only
    required field beyond `company`, mirroring
    apps.clients.validators.require_name exactly (Lead's identity fields
    are a direct carry-over of Client's own).
    """
    if not name or not name.strip():
        raise ValueError("Lead name cannot be blank or empty.")
    return name.strip()


def require_loss_reason(loss_reason: str) -> str:
    """
    Enforce a non-blank loss reason — FRS §8's own explicit requirement
    ("Lost leads require a loss reason"). Consumed only by
    LeadService.mark_lost.
    """
    if not loss_reason or not loss_reason.strip():
        raise ValueError("A loss reason is required to mark a lead as lost.")
    return loss_reason.strip()
