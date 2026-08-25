# BOQ API (Draft)
## INT Projects — Multi-Company Interior & Architecture Management SaaS

**Status:** Draft endpoint sketch.

---

## Scope

Product/Category catalog and BOQ (Bill of Quantities), which bridges the product catalog to a project and feeds the Quotation module.

## Product Catalog

| Method | Path | Purpose | Permission |
|---|---|---|---|
| GET | `/companies/{companyId}/product-categories` | List categories | `product.view` |
| POST | `/companies/{companyId}/product-categories` | Create category | `product.manage` |
| GET | `/companies/{companyId}/product-categories/{categoryId}/subcategories` | List subcategories | `product.view` |
| POST | `/companies/{companyId}/product-categories/{categoryId}/subcategories` | Create subcategory | `product.manage` |
| GET | `/companies/{companyId}/products` | List products (filter: category, subcategory, status) | `product.view` |
| POST | `/companies/{companyId}/products` | Create product/work item (unit, default cost, default rate, tax, status) | `product.manage` |
| PATCH | `/companies/{companyId}/products/{productId}` | Edit product | `product.manage` |

## BOQ

| Method | Path | Purpose | Permission |
|---|---|---|---|
| GET | `/companies/{companyId}/projects/{projectId}/boq` | Get project's BOQ (sections + items) | `project.view` |
| POST | `/companies/{companyId}/projects/{projectId}/boq/sections` | Add a section | `project.edit` |
| POST | `/companies/{companyId}/projects/{projectId}/boq/sections/{sectionId}/items` | Add item (product reference or free-text description, quantity, unit, rate) | `project.edit` |
| PATCH | `/companies/{companyId}/projects/{projectId}/boq/items/{itemId}` | Edit item (quantity/rate/discount/tax/notes/optional/alternative flags) | `project.edit` |
| DELETE | `/companies/{companyId}/projects/{projectId}/boq/items/{itemId}` | Remove item | `project.edit` |
| GET | `/companies/{companyId}/projects/{projectId}/boq/summary` | Computed subtotal/discount/tax/total | `project.view` |

## Notes

- `amount = quantity × rate` is computed server-side on every item write, never trusted from the client, since it feeds directly into quotation totals.
- A BOQ item may optionally reference a catalog `product` (to inherit default cost/rate/unit/tax) or be a free-text line item — both must be supported per the source requirement's "Section → Item" model.
- Optional and alternative items must be excluded from the default total but retrievable for quotation variants — confirm with client whether alternates are quotation-level or BOQ-level concepts (open item, see `Database_Schema.md` §Open Items).
