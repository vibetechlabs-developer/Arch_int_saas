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

    Foundation + CRUD (BE-031); Product is BE-033's own task — deliberately
    not pre-created here even though all three end up in this same app
    (00_Development_Standards/Folder_Structure.md §2a groups them under
    one `apps.products`), to keep task boundaries the same incremental
    shape as Client/Project's (BE-022/024) rather than pre-building empty
    stub models for later tasks.
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


class ProductSubcategory(BaseModel):
    """
    Second level of the Product catalog hierarchy (BE-032). Field set
    matches Database_Schema.md's `product_subcategory(id, company_id,
    category_id FK, name)` exactly — `company` is its own column (not
    merely derived through `category`), matching the schema's explicit
    column list and the same tenant-isolation-by-direct-FK pattern every
    other tenant-owned table in this codebase uses.

    `category` uses CASCADE, not PROTECT — unlike `Project.client`, no
    doc names this relationship as an example requiring hard-delete
    protection (Naming_Standards.md §4's own literal example was
    specifically "don't allow deleting a client with existing projects");
    a plain catalog parent/child hierarchy defaults to the more common
    CASCADE convention used by CompanyMembership/ProjectMember/etc.
    Application-level soft-delete guards (blocking a Category delete
    while active Subcategories exist, and a Subcategory delete while
    active Products exist) are separate from this FK's hard-delete
    behavior — see ProductCategoryService.soft_delete_category and
    ProductSubcategoryService.soft_delete_subcategory.
    """

    company = models.ForeignKey(
        "company.Company",
        on_delete=models.CASCADE,
        related_name="product_subcategories",
        db_index=True,
        help_text="The tenant company this subcategory belongs to.",
    )
    category = models.ForeignKey(
        ProductCategory,
        on_delete=models.CASCADE,
        related_name="subcategories",
        db_index=True,
        help_text="The parent category this subcategory belongs to.",
    )
    name = models.CharField(
        max_length=255,
        help_text="Subcategory name.",
    )

    class Meta:
        db_table = "product_subcategory"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["company", "category"], name="prod_subcat_comp_cat_idx"),
        ]
        verbose_name = "product subcategory"
        verbose_name_plural = "product subcategories"

    def __str__(self) -> str:
        return f"{self.name} ({self.category.name})"
