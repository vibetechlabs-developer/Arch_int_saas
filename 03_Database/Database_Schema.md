# Database Schema (Draft)
## INT Projects — Multi-Company Interior & Architecture Management SaaS

**Status:** Draft proposal for MVP (Phase 1–2) scope only — **not final**, pending client sign-off on business/functional requirements and the multi-tenancy strategy decision in `02_Architecture/Technical_Architecture.md` §3. Column types are indicative (PostgreSQL).

---

## Conventions

- Every tenant-owned table has a `company_id UUID NOT NULL REFERENCES company(id)` column and an index on it — see `Naming_Standards.md`.
- Every table has `id UUID PRIMARY KEY DEFAULT gen_random_uuid()`, `created_at TIMESTAMPTZ NOT NULL DEFAULT now()`, `updated_at TIMESTAMPTZ NOT NULL DEFAULT now()`.
- Soft delete via `deleted_at TIMESTAMPTZ NULL` is recommended for business records (clients, projects, quotations, invoices) to preserve audit/history; hard delete only for platform-admin-initiated tenant offboarding.

---

## Platform Layer (not tenant-scoped)

### `platform_admin`
| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| email | TEXT UNIQUE | |
| password_hash | TEXT | |
| status | TEXT | active/suspended |

### `company` (tenant)
| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| name | TEXT | |
| status | TEXT | trial/active/suspended |
| plan_id | UUID FK → `plan.id` | |
| currency | TEXT | |
| gst_number | TEXT | nullable |
| settings | JSONB | numbering, payment terms, notification prefs |

### `plan`, `subscription`
- `plan(id, name, price, limits JSONB, features JSONB)`
- `subscription(id, company_id FK, plan_id FK, status, started_at, renews_at)`

### `audit_log`
| Column | Type | Notes |
|---|---|---|
| id | UUID PK | |
| company_id | UUID FK, nullable | null for platform-level actions |
| actor_user_id | UUID FK | |
| entity_type | TEXT | e.g. `invoice`, `quotation` |
| entity_id | UUID | |
| action | TEXT | create/update/delete/approve |
| old_value | JSONB | |
| new_value | JSONB | |
| created_at | TIMESTAMPTZ | |

---

## Company Layer (tenant-scoped: all tables below carry `company_id`)

### `user`
| id | UUID PK |
|---|---|
| email | TEXT UNIQUE (global) |
| password_hash | TEXT |
| name | TEXT |
| status | active/inactive |
| last_login_at | TIMESTAMPTZ |

### `company_membership`
| Column | Notes |
|---|---|
| id | UUID PK |
| company_id | FK |
| user_id | FK |
| role_id | FK → `role.id` |
| status | active/invited/revoked |

A `user` row is global (one login can belong to multiple companies); `company_membership` is where role and tenant scope actually live.

### `role`, `permission`, `role_permission`
- `role(id, company_id, name)` — company_id nullable for platform-defined default roles (Owner/Admin/PM/Designer/Accountant/Sales)
- `permission(id, code)` — e.g. `invoice.view`, `invoice.create`, `expense.approve`
- `role_permission(role_id, permission_id)`

### `client`
| id, company_id | name | company_name | email | mobile | gstin | addresses (JSONB or separate `client_address` table) | notes |

### `project`
| id, company_id | client_id FK | name | start_date | deadline | status | priority | assigned_to (user_id) | follow_up_reminder_at |

Status enum: `draft, planning, design, quotation, approved, execution, quality_check, handover, completed, on_hold, cancelled`

### `product_category`, `product_subcategory`, `product`
- `product_category(id, company_id, name)`
- `product_subcategory(id, company_id, category_id FK, name)`
- `product(id, company_id, subcategory_id FK, name, image_url, unit, default_cost, default_selling_rate, tax_rate, status)`

### `boq`, `boq_section`, `boq_item`
- `boq(id, company_id, project_id FK, status)`
- `boq_section(id, boq_id FK, name, sort_order)`
- `boq_item(id, boq_section_id FK, product_id FK nullable, description, quantity, unit, rate, discount, tax, amount, is_optional, is_alternative, notes)`

### `quotation`, `quotation_item`
- `quotation(id, company_id, project_id FK, boq_id FK nullable, quote_number, version, client_id FK, subtotal, discount, tax, total, terms, payment_schedule JSONB, valid_until, status, notes)`
  - status enum: `draft, internal_review, sent, revision_requested, approved, rejected`
- `quotation_item(id, quotation_id FK, product_id FK nullable, description, quantity, unit, rate, amount)`

### `contract`
| id, company_id | project_id FK | quotation_id FK | terms | scope | payment_schedule JSONB | status | client_accepted_at |

### `invoice`, `invoice_item`
- `invoice(id, company_id, project_id FK, contract_id FK nullable, quotation_id FK nullable, invoice_number, client_id FK, subtotal, discount, tax, total, due_date, payment_terms, status, notes)`
  - status enum: `draft, sent, partially_paid, paid, overdue, cancelled`
- `invoice_item(id, invoice_id FK, description, quantity, unit, rate, amount)`

### `payment`
| id, company_id | invoice_id FK | client_id FK | project_id FK | payment_date | amount | method | reference_number | receipt_url | notes |

### `expense`
| id, company_id | project_id FK | category | vendor | employee_id FK nullable | amount | tax | date | payment_method | receipt_url | notes | added_by (user_id) | approval_status |

approval_status enum: `draft, submitted, approved, paid`

### `task`, `document`
- `task(id, company_id, project_id FK, title, assigned_to FK, due_date, status)`
- `document(id, company_id, project_id FK, entity_type, entity_id, file_url, version, uploaded_by FK, uploaded_at)`

---

## Phase 3+ Tables (reference only — not MVP)

`lead`, `site_visit`, `design`, `design_version`, `vendor`, `purchase_request`, `purchase_order`, `inventory_item`, `site_daily_log`, `snag`, `handover`, `notification`.

---

## Open Items Before This Schema Is Finalized

1. Confirm multi-tenancy isolation strategy (`02_Architecture/Technical_Architecture.md` §3) — affects whether `company_id` alone is sufficient or Postgres RLS policies are also required.
2. Confirm quotation/invoice numbering rules (per-company sequence vs. global) — affects whether `quote_number`/`invoice_number` needs a separate sequence table per company.
3. Confirm whether BOQ versioning is required (client doc doesn't explicitly call for BOQ revision history the way it does for Quotations and Designs).
4. Confirm currency handling — single currency per company vs. per-project.

See `03_Database/Naming_Standards.md` for column/table naming conventions used above.
