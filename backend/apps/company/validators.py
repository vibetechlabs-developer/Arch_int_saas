from typing import Any, Dict, Optional

from apps.company.models import get_default_company_settings


def build_create_fields(
    name: str,
    currency: str,
    gst_number: Optional[str],
    status: str,
    settings: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Normalize raw Company creation input into persistence-ready fields.
    """
    company_settings = get_default_company_settings()
    if settings and isinstance(settings, dict):
        company_settings.update(settings)

    return {
        "name": name.strip(),
        "currency": currency.strip(),
        "gst_number": gst_number.strip() if gst_number else None,
        "status": status,
        "settings": company_settings,
    }


def build_update_fields(
    validated_data: Dict[str, Any],
    current_settings: Dict[str, Any],
    is_platform_admin: bool,
) -> Dict[str, Any]:
    """
    Normalize raw Company update input into persistence-ready fields.
    Tenant status may only be changed by a Platform Admin.
    """
    fields: Dict[str, Any] = {}

    if "name" in validated_data:
        fields["name"] = validated_data["name"].strip()

    if "currency" in validated_data:
        fields["currency"] = validated_data["currency"].strip()

    if "gst_number" in validated_data:
        fields["gst_number"] = (
            validated_data["gst_number"].strip() if validated_data["gst_number"] else None
        )

    if "logo_url" in validated_data:
        fields["logo_url"] = validated_data["logo_url"] or ""
        # Mirrors ProductService.update_product's invariant: logo_url and
        # logo_storage_key must never drift out of sync -- a fresh
        # logoUrl always carries either a real logoStorageKey (an actual
        # upload) or resets to "" (manual URL entry / explicit removal).
        fields["logo_storage_key"] = validated_data.get("logo_storage_key") or ""

    if "status" in validated_data and is_platform_admin:
        fields["status"] = validated_data["status"]

    if "settings" in validated_data and isinstance(validated_data["settings"], dict):
        merged_settings = dict(current_settings or {})
        merged_settings.update(validated_data["settings"])
        fields["settings"] = merged_settings

    return fields
