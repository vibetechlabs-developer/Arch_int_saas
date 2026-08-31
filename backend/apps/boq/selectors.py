import uuid

from apps.boq.models import BOQItem


def has_active_items_for_section(section_id: str | uuid.UUID) -> bool:
    """
    True if the given section (by ID) has at least one non-deleted
    BOQItem. Backs BOQSectionService.soft_delete_section's delete guard
    (resolves BE-035's documented deferral) — a plain module-level
    function, matching apps.products' has_active_subcategories_for_category
    reasoning: Section and Item live in the same app, so no cross-app
    domain-ownership indirection is needed.
    """
    return BOQItem.objects.filter(boq_section_id=section_id).exists()
