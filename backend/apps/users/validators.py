from typing import Optional

from rest_framework import exceptions as drf_exceptions


def clean_role_name(name: str) -> str:
    """
    Trim a Role name and reject a blank/whitespace-only value.
    """
    cleaned = name.strip()
    if not cleaned:
        raise drf_exceptions.ValidationError({"name": ["Role name cannot be blank or empty."]})
    return cleaned


def clean_role_description(description: Optional[str]) -> str:
    return description.strip() if description else ""


def clean_email(email: str) -> str:
    cleaned = email.strip().lower()
    if not cleaned:
        raise drf_exceptions.ValidationError({"email": ["Email cannot be blank or empty."]})
    return cleaned


def validate_role_belongs_to_company(role, company_id) -> None:
    """
    A membership's role must belong to the same company as the membership
    itself — there is no DB constraint enforcing this (Django has no native
    cross-field FK-company-match constraint), so it's enforced here on
    every assignment.
    """
    if str(role.company_id) != str(company_id):
        raise drf_exceptions.ValidationError(
            {"roleId": ["This role does not belong to the same company as this membership."]}
        )


def validate_role_is_active(role) -> None:
    """
    An inactive role cannot be newly assigned to a membership (BE-054
    §10) — a role can be deactivated without being deleted (e.g. while a
    Company Admin reworks its permission set), and that should block new
    assignments even though existing holders' access is governed purely
    by PermissionService's own is_active check, not this one.
    """
    if not role.is_active:
        raise drf_exceptions.ValidationError(
            {"roleId": ["This role is inactive and cannot be assigned."]}
        )
