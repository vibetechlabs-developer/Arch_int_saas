import uuid

from django.db.models import QuerySet

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


def list_includible_items_for_boq(boq_id: str | uuid.UUID) -> QuerySet[BOQItem]:
    """
    All non-deleted BOQItems across every Section of the given BOQ,
    excluding items flagged `is_optional`/`is_alternative` — per
    BOQ_API.md's Notes: "Optional and alternative items must be excluded
    from the default total". Backs BOQSummaryService.compute_summary
    (BE-037).
    """
    return BOQItem.objects.filter(
        boq_section__boq_id=boq_id, is_optional=False, is_alternative=False
    )
