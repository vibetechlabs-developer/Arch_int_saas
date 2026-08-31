from django.db import models

from apps.common.models import BaseModel


class BOQ(BaseModel):
    """
    Tenant-scoped Bill of Quantities — one per Project (Migration_Plan.md's
    own stated rationale for table position 016: "One BOQ per project"),
    hence `project` is a OneToOneField, not a plain FK. Field set matches
    Database_Schema.md's `boq(id, company_id, project_id FK, status)`
    exactly.

    Auto-created on first access (Backend Lead decision, AskUserQuestion,
    2026-08-31): BOQ_API.md documents no `POST .../boq` endpoint at all —
    only `GET .../boq` and `POST .../boq/sections` — consistent with BOQ
    being an implicit 1:1 companion to Project rather than something
    explicitly created. See BOQService.get_or_create_boq_for_project.

    `status` has no documented value domain anywhere (unlike Project/
    Company, which have documented enums) and no endpoint in BOQ_API.md
    ever reads or writes it — left an unconstrained CharField rather than
    an invented enum, the same treatment Project.priority got when no
    domain was documented (a closer analogy here than Product.status,
    which had an obvious real-world Active/Inactive meaning this field
    doesn't).
    """

    company = models.ForeignKey(
        "company.Company",
        on_delete=models.CASCADE,
        related_name="boqs",
        db_index=True,
        help_text="The tenant company this BOQ belongs to.",
    )
    project = models.OneToOneField(
        "projects.Project",
        on_delete=models.CASCADE,
        related_name="boq",
        help_text="The project this BOQ belongs to. One BOQ per project.",
    )
    status = models.CharField(
        max_length=50,
        blank=True,
        default="",
        help_text="Free-text BOQ status. No documented value domain exists.",
    )

    class Meta:
        db_table = "boq"
        ordering = ["-created_at"]
        verbose_name = "BOQ"
        verbose_name_plural = "BOQs"

    def __str__(self) -> str:
        return f"BOQ for {self.project.name}"


class BOQSection(BaseModel):
    """
    A named, ordered grouping of BOQItems within one BOQ (BE-035). Field
    set matches Database_Schema.md's `boq_section(id, boq_id FK, name,
    sort_order)` exactly — note there is deliberately **no** `company`
    column here, matching the schema literally (unlike every other
    tenant-owned table built so far in this codebase, which all had a
    denormalized `company` FK). Tenant scoping for a Section resolves
    through `boq.company_id`, not a column on this table.

    `sort_order` is auto-assigned by BOQService.create_section (append to
    the end of the BOQ's existing sections) — BOQ_API.md's "Add a
    section" row lists no input fields at all beyond implying a name, so
    no manual sort_order input is exposed; reordering is out of this
    sprint's documented scope.
    """

    boq = models.ForeignKey(
        BOQ,
        on_delete=models.CASCADE,
        related_name="sections",
        db_index=True,
        help_text="The BOQ this section belongs to.",
    )
    name = models.CharField(
        max_length=255,
        help_text="Section name.",
    )
    sort_order = models.PositiveIntegerField(
        default=0,
        help_text="Display order among this BOQ's sections (auto-assigned).",
    )

    class Meta:
        db_table = "boq_section"
        ordering = ["sort_order", "created_at"]
        verbose_name = "BOQ section"
        verbose_name_plural = "BOQ sections"

    def __str__(self) -> str:
        return f"{self.name} (BOQ {self.boq_id})"
