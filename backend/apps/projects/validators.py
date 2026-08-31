import uuid

from rest_framework import exceptions as drf_exceptions

from apps.users.models import CompanyMembership, CompanyMembershipStatus


def require_name(name: str) -> str:
    """
    Enforce Project.name is present and non-blank — mirrors
    apps.clients.validators.require_name.
    """
    if not name or not name.strip():
        raise ValueError("Project name cannot be blank or empty.")
    return name.strip()


def validate_assignee_company_membership(user_id: str | uuid.UUID, company_id: str | uuid.UUID) -> None:
    """
    Enforce the documented invariant (BE-024 §"assigned_to Strategy",
    confirmed in BE-025 planning): assigned_to must belong to an ACTIVE
    CompanyMembership in the same company as the Project. Matches
    05_Security/Tenant.md §2's exact bar ("active company_membership") —
    INVITED/REVOKED memberships, and soft-deleted membership rows
    (excluded by the default manager automatically), do not qualify.
    """
    is_member = CompanyMembership.objects.filter(
        user_id=user_id,
        company_id=company_id,
        status=CompanyMembershipStatus.ACTIVE,
    ).exists()

    if not is_member:
        raise drf_exceptions.ValidationError(
            {"assignedTo": ["assignedTo must be an active member of this company."]}
        )
