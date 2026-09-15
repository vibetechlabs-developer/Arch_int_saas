def require_lead_or_project(lead_id, project_id) -> None:
    """
    FRS §9 / ER_Diagram.md §2: a site visit is always scheduled against
    either a Lead or a Project (or both, e.g. a visit against a project
    whose originating lead is still tracked) -- never neither.
    """
    if not lead_id and not project_id:
        raise ValueError("A site visit must be linked to a lead or a project (or both).")
