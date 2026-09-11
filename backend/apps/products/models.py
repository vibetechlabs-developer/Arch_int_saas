from django.db import models
from django.utils.translation import gettext_lazy as _

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


class ProductUnit(models.TextChoices):
    """
    01_Business/FRS.md §11's documented 8-value list — the one Product
    field with an actual enumerated value domain (unlike `status`, which
    has none documented anywhere; see ProductStatus below for that
    Backend Lead decision).
    """

    NOS = "nos", _("Nos")
    SQFT = "sqft", _("Sq.ft")
    SQM = "sqm", _("Sq.m")
    RUNNING_FT = "running_ft", _("Running ft")
    KG = "kg", _("Kg")
    LITRE = "litre", _("Litre")
    SET = "set", _("Set")
    JOB = "job", _("Job")


class ProductStatus(models.TextChoices):
    """
    Database_Schema.md and FRS.md both list a `status` field on `product`
    but never enumerate its values (unlike Company/Project, which have
    documented enums). Backend Lead decision (AskUserQuestion, 2026-08-31):
    a simple Active/Inactive enum — the standard catalog pattern where an
    inactive product stays in the system for historical BOQ/Quotation
    references but can't be selected for new items (that exclusion is
    BE-034/BOQ's job to enforce, not this model).
    """

    ACTIVE = "active", _("Active")
    INACTIVE = "inactive", _("Inactive")


class Product(BaseModel):
    """
    Third level of the Product catalog hierarchy (BE-033) — the actual
    catalog item/work item BOQ items can reference (Database_Schema.md's
    `boq_item.product_id`, nullable, is built in a later sprint). Field
    set matches `product(id, company_id, subcategory_id FK, name,
    image_url, unit, default_cost, default_selling_rate, tax_rate,
    status)` exactly. Only `company`/`subcategory`/`name` are required —
    the remaining fields (image, unit, pricing, tax) are treated as detail
    fields that may be filled in later, mirroring Project's own
    only-the-identifying-fields-are-required approach (BE-024/025).

    `subcategory` uses CASCADE, matching ProductSubcategory.category's own
    reasoning (BE-032) — no doc names this relationship as needing
    hard-delete protection.

    Money fields use `NUMERIC(14,2)` (03_Database/Naming_Standards.md's
    documented convention for money columns) via
    `DecimalField(max_digits=14, decimal_places=2)`. `tax_rate` is a
    percentage, not money — `max_digits=5, decimal_places=2` (up to
    999.99%) is a plain numeric-precision choice, not a business rule.
    """

    company = models.ForeignKey(
        "company.Company",
        on_delete=models.CASCADE,
        related_name="products",
        db_index=True,
        help_text="The tenant company this product belongs to.",
    )
    subcategory = models.ForeignKey(
        ProductSubcategory,
        on_delete=models.CASCADE,
        related_name="products",
        db_index=True,
        help_text="The subcategory this product belongs to.",
    )
    name = models.CharField(
        max_length=255,
        help_text="Product/work item name.",
    )
    image_url = models.URLField(
        max_length=500,
        blank=True,
        default="",
        help_text="URL of the product's image, if any.",
    )
    image_storage_key = models.CharField(
        max_length=500,
        blank=True,
        default="",
        help_text=(
            "Internal-only (never serialized). The object-storage key "
            "backing image_url, set only when the image was uploaded via "
            "POST /products/images/upload (BE-078). Blank when image_url "
            "was entered manually via the alternate URL-entry flow -- in "
            "that case this app does not own the file and must never "
            "attempt to delete it. Used by ProductService.update_product "
            "to safely clean up a superseded image on replace/remove "
            "without ever deleting a file this app doesn't own."
        ),
    )
    unit = models.CharField(
        max_length=20,
        choices=ProductUnit.choices,
        blank=True,
        default="",
        help_text="Unit of measure. One of the 8 documented values.",
    )
    default_cost = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Default cost price for this product.",
    )
    default_selling_rate = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Default selling rate for this product.",
    )
    tax_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Tax rate percentage applied to this product by default.",
    )
    status = models.CharField(
        max_length=20,
        choices=ProductStatus.choices,
        default=ProductStatus.ACTIVE,
        db_index=True,
        help_text="Product catalog status.",
    )

    class Meta:
        db_table = "product"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["company", "status"], name="product_company_status_idx"),
            models.Index(fields=["subcategory"], name="product_subcategory_idx"),
        ]
        verbose_name = "product"
        verbose_name_plural = "products"

    def __str__(self) -> str:
        return f"{self.name} ({self.company.name})"
