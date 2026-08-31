import uuid
from typing import Any, Dict, Optional

from django.db.models import QuerySet
from rest_framework import exceptions as drf_exceptions

from apps.boq.models import BOQ, BOQItem, BOQSection
from apps.projects.models import Project


class BOQRepository:
    """
    Data-access layer for BOQ (BE-035). Mirrors the established
    Repository pattern (BACKEND_RULES.md: View -> Serializer -> Service ->
    Repository -> Model).
    """

    @staticmethod
    def get_by_project(project: Project) -> Optional[BOQ]:
        return BOQ.objects.select_related("company", "project").filter(project=project).first()

    @staticmethod
    def create_for_project(project: Project) -> BOQ:
        return BOQ.objects.create(company=project.company, project=project)

    @staticmethod
    def get_by_id(boq_id: str | uuid.UUID) -> BOQ:
        try:
            return BOQ.objects.select_related("company", "project").get(id=boq_id)
        except (BOQ.DoesNotExist, ValueError):
            raise drf_exceptions.NotFound("The requested BOQ was not found.")

    @staticmethod
    def save(boq: BOQ, fields: Optional[Dict[str, Any]] = None) -> BOQ:
        for field, value in (fields or {}).items():
            setattr(boq, field, value)
        boq.save()
        return boq


class BOQSectionRepository:
    """
    Data-access layer for BOQSection (BE-035).
    """

    @staticmethod
    def all_for_boq(boq_id: str | uuid.UUID) -> QuerySet[BOQSection]:
        return BOQSection.objects.select_related("boq", "boq__company").filter(boq_id=boq_id)

    @staticmethod
    def get_by_id(section_id: str | uuid.UUID) -> BOQSection:
        try:
            return BOQSection.objects.select_related("boq", "boq__company").get(id=section_id)
        except (BOQSection.DoesNotExist, ValueError):
            raise drf_exceptions.NotFound("The requested BOQ section was not found.")

    @staticmethod
    def max_sort_order_for_boq(boq_id: str | uuid.UUID) -> int:
        result = BOQSection.objects.filter(boq_id=boq_id).order_by("-sort_order").values_list(
            "sort_order", flat=True
        ).first()
        return result or 0

    @staticmethod
    def create(**fields: Any) -> BOQSection:
        return BOQSection.objects.create(**fields)

    @staticmethod
    def save(section: BOQSection, fields: Optional[Dict[str, Any]] = None) -> BOQSection:
        for field, value in (fields or {}).items():
            setattr(section, field, value)
        section.save()
        return section

    @staticmethod
    def soft_delete(section: BOQSection) -> None:
        section.delete()


class BOQItemRepository:
    """
    Data-access layer for BOQItem (BE-036).
    """

    @staticmethod
    def all_for_section(section_id: str | uuid.UUID) -> QuerySet[BOQItem]:
        return BOQItem.objects.select_related(
            "boq_section", "boq_section__boq", "boq_section__boq__company", "product"
        ).filter(boq_section_id=section_id)

    @staticmethod
    def get_by_id(item_id: str | uuid.UUID) -> BOQItem:
        try:
            return BOQItem.objects.select_related(
                "boq_section", "boq_section__boq", "boq_section__boq__company", "product"
            ).get(id=item_id)
        except (BOQItem.DoesNotExist, ValueError):
            raise drf_exceptions.NotFound("The requested BOQ item was not found.")

    @staticmethod
    def create(**fields: Any) -> BOQItem:
        return BOQItem.objects.create(**fields)

    @staticmethod
    def save(item: BOQItem, fields: Optional[Dict[str, Any]] = None) -> BOQItem:
        for field, value in (fields or {}).items():
            setattr(item, field, value)
        item.save()
        return item

    @staticmethod
    def soft_delete(item: BOQItem) -> None:
        item.delete()
