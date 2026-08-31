import uuid
from typing import Any, Dict, Optional
from django.db import transaction
from django.db.models import QuerySet
from rest_framework import exceptions as drf_exceptions

from apps.audit.models import AuditAction
from apps.audit.services import AuditLogService
from apps.boq import validators
from apps.boq.models import BOQ, BOQSection
from apps.boq.repositories import BOQRepository, BOQSectionRepository
from apps.projects.models import Project

SECTION_AUDITED_FIELDS = ("name", "sort_order")


def _section_audit_state(section: BOQSection) -> Dict[str, Any]:
    return {field: getattr(section, field) for field in SECTION_AUDITED_FIELDS}


class BOQService:
    """
    Business logic and orchestration service for BOQ management (BE-035).
    BOQ has no create/update/delete endpoint of its own — it is an
    implicit 1:1 companion to Project, auto-created on first access
    (Backend Lead decision, 2026-08-31). Audit logging wired inline, not
    deferred — Sprint 4 has no separate "Audit Logs" task, mirroring
    Sprint 3's Product Catalog precedent (BE-031) rather than Project's
    BE-024-029 split.
    """

    @classmethod
    def get_or_create_boq_for_project(
        cls,
        project: Project,
        actor_user: Any = None,
        request: Any = None,
    ) -> BOQ:
        """
        Fetch the given Project's BOQ, creating one if it doesn't exist
        yet. Idempotent — a second call for the same project returns the
        existing row, never creates a duplicate (backed by `project`
        being a OneToOneField).
        """
        boq = BOQRepository.get_by_project(project)
        if boq is not None:
            return boq

        with transaction.atomic():
            boq = BOQRepository.create_for_project(project)

            AuditLogService.record(
                action=AuditAction.CREATE,
                entity_type="boq",
                entity_id=boq.id,
                company_id=project.company_id,
                actor_user=actor_user,
                after_state={"project_id": str(project.id)},
                request=request,
            )

            return boq


class BOQSectionService:
    """
    Business logic and orchestration service for BOQSection management
    (BE-035). Every method takes an already-authorized `boq` instance
    (tenant authorization for the parent Project/BOQ happens at the view
    layer, mirroring ProjectMemberService's pattern) — except
    get/update/delete-by-id, which resolve tenant scope through
    `section.boq.company_id` since BOQSection has no direct company
    column (Database_Schema.md's own schema, not an oversight).
    """

    @classmethod
    def list_sections(cls, boq: BOQ) -> QuerySet[BOQSection]:
        return BOQSectionRepository.all_for_boq(boq.id)

    @classmethod
    def create_section(
        cls,
        boq: BOQ,
        name: str,
        actor_user: Any = None,
        request: Any = None,
    ) -> BOQSection:
        """
        Create a new BOQSection, appended to the end of the BOQ's existing
        sections. `sort_order` is auto-assigned (max existing + 1) — not
        an input field, per BOQ_API.md's "Add a section" row listing no
        fields at all beyond implying a name.
        """
        with transaction.atomic():
            cleaned_name = validators.require_section_name(name)
            next_sort_order = BOQSectionRepository.max_sort_order_for_boq(boq.id) + 1

            section = BOQSectionRepository.create(
                boq=boq, name=cleaned_name, sort_order=next_sort_order
            )

            AuditLogService.record(
                action=AuditAction.CREATE,
                entity_type="boq_section",
                entity_id=section.id,
                company_id=boq.company_id,
                actor_user=actor_user,
                after_state=_section_audit_state(section),
                request=request,
            )

            return section

    @classmethod
    def get_section_by_id(
        cls,
        section_id: str | uuid.UUID,
        company_id: Optional[str | uuid.UUID] = None,
    ) -> BOQSection:
        """
        Retrieve an active, non-deleted BOQSection by primary key UUID.
        Raises NotFound if it does not exist, is soft-deleted, or its
        parent BOQ belongs to another company.
        """
        section = BOQSectionRepository.get_by_id(section_id)

        if company_id is not None and str(section.boq.company_id) != str(company_id):
            raise drf_exceptions.NotFound("The requested BOQ section was not found.")

        return section

    @classmethod
    def update_section(
        cls,
        section_id: str | uuid.UUID,
        validated_data: Dict[str, Any],
        company_id: Optional[str | uuid.UUID] = None,
        actor_user: Any = None,
        request: Any = None,
    ) -> BOQSection:
        """
        Update an existing BOQSection's name. Added for consistency with
        every other module in this codebase (BOQ_API.md documents no
        PATCH for sections at all) — the same "add missing CRUD" Backend
        Lead decision BE-031 established for Category/Subcategory/Product
        DELETE.
        """
        with transaction.atomic():
            section = cls.get_section_by_id(section_id, company_id=company_id)
            before_state = _section_audit_state(section)

            fields: Dict[str, Any] = {}
            if "name" in validated_data:
                fields["name"] = validators.require_section_name(validated_data["name"])

            section = BOQSectionRepository.save(section, fields)

            AuditLogService.record(
                action=AuditAction.UPDATE,
                entity_type="boq_section",
                entity_id=section.id,
                company_id=section.boq.company_id,
                actor_user=actor_user,
                before_state=before_state,
                after_state=_section_audit_state(section),
                request=request,
            )

            return section

    @classmethod
    def soft_delete_section(
        cls,
        section_id: str | uuid.UUID,
        company_id: Optional[str | uuid.UUID] = None,
        actor_user: Any = None,
        request: Any = None,
    ) -> None:
        """
        Soft-delete a BOQSection. Deferred (documented, not a gap, mirrors
        BE-031/032's identical Category->Subcategory deferral chain): the
        "block delete if active Items exist" guard can't be built until
        BE-036 (BOQItem) exists. BE-036 adds it.
        """
        with transaction.atomic():
            section = cls.get_section_by_id(section_id, company_id=company_id)
            section_id_val = section.id
            company_id_val = section.boq.company_id
            before_state = _section_audit_state(section)

            BOQSectionRepository.soft_delete(section)

            AuditLogService.record(
                action=AuditAction.DELETE,
                entity_type="boq_section",
                entity_id=section_id_val,
                company_id=company_id_val,
                actor_user=actor_user,
                before_state=before_state,
                request=request,
            )
