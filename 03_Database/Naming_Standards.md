# Database Naming Standards
## INT Projects — Multi-Company Interior & Architecture Management SaaS

**Status:** Draft proposal — general PostgreSQL conventions, to confirm with the engineering team before schema implementation begins.

---

## 1. Tables

- `snake_case`, singular noun (e.g. `project`, `invoice_item`, not `projects`/`invoiceItems`).
- Join/link tables named `entity_a_entity_b` in relationship order (e.g. `role_permission`, `company_membership`).
- Every tenant-owned table name should read naturally as "a company's X" (e.g. `client`, `expense`) — platform-only tables are prefixed conceptually by being listed under the Platform Layer in `Database_Schema.md`, not by a naming prefix.

## 2. Columns

- `snake_case`.
- Primary key: always `id` (UUID).
- Foreign keys: `<referenced_table>_id` (e.g. `project_id`, `client_id`). Where a table has two FKs to the same referenced table, disambiguate with a role prefix (e.g. `assigned_to_user_id` vs `added_by_user_id`).
- Tenant scope column: always `company_id`, always `NOT NULL`, always indexed, on every tenant-owned table.
- Timestamps: `created_at`, `updated_at` (both `TIMESTAMPTZ`), `deleted_at` (nullable, for soft delete).
- Booleans: prefixed `is_`/`has_` (e.g. `is_optional`, `has_attachments`).
- Money columns: store as `NUMERIC(14,2)` (not float), named plainly (`amount`, `total`, `subtotal`) — currency is inherited from the owning company unless multi-currency-per-project is confirmed.
- Status/enum columns: named `status` where there's one obvious status field per entity; use Postgres `ENUM` types or a `CHECK` constraint with a documented value list (see status enums in `Database_Schema.md`).

## 3. Indexes

- Every `company_id` column: indexed (supports tenant-scoped queries, which are the majority of all queries).
- Every foreign key: indexed.
- Composite index on `(company_id, <common filter column>)` for high-traffic list queries (e.g. `(company_id, status)` on `project`, `(company_id, client_id)` on `invoice`).

## 4. Constraints

- Foreign keys always declared with `ON DELETE RESTRICT` by default for business-critical references (e.g. don't allow deleting a `client` with existing `project`s); use soft delete (`deleted_at`) instead of hard delete for anything with audit/reporting implications.
- `NOT NULL` on `company_id` for every tenant-owned table — enforced at the schema level, not just the application level, as a backstop against tenant-isolation bugs.

## 5. Enum Value Naming

- `snake_case`, lowercase (e.g. `partially_paid`, `on_hold`).
- Documented centrally in `Database_Schema.md` next to the owning table, not scattered across application code comments.

## 6. Migrations

- One logical change per migration file.
- Migration filenames timestamp-prefixed (`YYYYMMDDHHMMSS_description.sql` or the equivalent for the chosen migration tool) to guarantee ordering.

## 7. Open Items

- Confirm the migration tool once the backend framework is chosen (`02_Architecture/Technical_Architecture.md` §8 Open Decisions).
- Confirm whether Postgres `ENUM` types or `CHECK` constraints are preferred (ENUM is stricter but harder to alter later; CHECK is more flexible).
