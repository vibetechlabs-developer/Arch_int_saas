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
