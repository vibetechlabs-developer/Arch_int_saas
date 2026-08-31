from django.db import models

from apps.common.models import BaseModel


class ProductCategory(BaseModel):
    """
    Tenant-scoped top level of the Product catalog hierarchy
    (Category -> Subcategory -> Product/Work Item, 01_Business/FRS.md §11,
    03_Database/Database_Schema.md). Field set matches Database_Schema.md's
    `product_category(id, company_id, name)` exactly — no invented fields
    (no uniqueness constraint on name — not documented, matching the
    Client precedent).

    Foundation + CRUD only (BE-031): ProductSubcategory/Product are BE-032/
    BE-033's own tasks — deliberately not pre-created here even though all
    three end up in this same app (00_Development_Standards/Folder_Structure.md
    §2a groups them under one `apps.products`), to keep task boundaries
    the same incremental shape as Client/Project's (BE-022/024) rather
    than pre-building empty stub models for later tasks.
    """

    company = models.ForeignKey(
        "company.Company",
        on_delete=models.CASCADE,
        related_name="product_categories",
        db_index=True,
        help_text="The tenant company this category belongs to.",
    )
    name = models.CharField(
        max_length=255,
        help_text="Category name.",
    )

    class Meta:
        db_table = "product_category"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["company", "name"], name="product_cat_comp_name_idx"),
        ]
        verbose_name = "product category"
        verbose_name_plural = "product categories"

    def __str__(self) -> str:
        return f"{self.name} ({self.company.name})"
