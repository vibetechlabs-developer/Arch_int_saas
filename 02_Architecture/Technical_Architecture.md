# Technical Architecture
## INT Projects — Multi-Company Interior & Architecture Management SaaS

**Status:** Draft — pending approval. Technology choices below are **proposed defaults**, not yet confirmed with the client — see Open Decisions.

---

## 1. Layered Architecture

```
Frontend (web app; client portal is a separate future surface)
   ↓
API / Application Layer (API-first, modular backend)
   ↓
Business Modules (Company, User, Client, Project, Product, BOQ,
                   Quotation, Contract, Invoice, Payment, Expense, Report, ...)
   ↓
Tenant / Permission Layer (middleware enforced on every request)
   ↓
PostgreSQL (system of record)
   ↓
Object/File Storage (designs, drawings, attachments, receipts)
```

## 2. Confirmed Technology Stack

The stack below is now client-confirmed (supersedes the "Open Decisions" placeholder that previously covered backend/frontend framework choice):

**Frontend**
- React + TypeScript, built with Vite
- Tailwind CSS for styling, shadcn/ui as the component primitive layer
- Lucide as the sole icon library (`00_Development_Standards/Naming_Conventions.md` §6 note — no mixing icon sets)
- Motion / Framer Motion for animation
- See `06_UI/` for the full design system (tokens, components, shell, responsive/accessibility strategy) built on this stack

**Backend**
- Django + Django REST Framework (DRF)
- Backend modules map to Django apps, one per business module (`company`, `client`, `project`, `boq`, `quotation`, `invoice`, `payment`, `expense`, `report`, ...) — see `00_Development_Standards/Folder_Structure.md` §2a for the Django-specific layering convention
- Backend code follows PEP 8 naming (`snake_case`), distinct from the frontend's TypeScript conventions — see `00_Development_Standards/Naming_Conventions.md` §7

**Database & Storage**
- PostgreSQL as the system of record (confirmed independently of this stack decision, see below)
- Object/file storage separate from PostgreSQL for versioned design files, drawings, receipts, attachments

## 2a. Confirmed Technical Requirements (from source requirements doc)

- **Database:** PostgreSQL — explicitly specified as the system of record.
- **File storage:** Object/file storage layer, separate from the relational database, for documents, design files (versioned), drawings, receipts, and attachments.
- **API-first:** all business logic exposed through an API layer; frontend and future client portal both consume it.
- **Modular backend:** business modules (Company, Client, Project, Product, BOQ, Quotation, Invoice, Payment, Expense, Report, ...) should be separable, not a monolith of ad-hoc screens.
- **Tenant/Permission layer must sit between the API and the business modules** — every request resolves user → company membership → role → permission before touching business logic or data (see `05_Security/Tenant.md` and `05_Security/Permissions.md`).
- **Frontend must be permission-driven**, but the API is the actual enforcement boundary — the frontend must never be trusted to supply a company ID for authorization.

## 3. Multi-Tenancy Strategy (to confirm)

Options to evaluate against the client's isolation requirement ("Company A must never access Company B's data"):

| Strategy | Isolation Strength | Operational Complexity |
|---|---|---|
| Shared DB, shared schema, `company_id` on every row + row-level enforcement | Depends entirely on correct enforcement everywhere | Lowest |
| Shared DB, schema-per-tenant | Stronger | Medium |
| Database-per-tenant | Strongest | Highest, harder to scale to many small tenants |

**Recommendation (pending client confirmation):** shared DB / shared schema with `company_id` on every tenant-owned table, enforced by a mandatory tenant-scoping layer (e.g., middleware + query-builder guard, or Postgres Row-Level Security as a defense-in-depth backstop) — balances the client's likely SMB tenant count/size against operational simplicity. This must be re-evaluated once expected tenant count and data-sensitivity requirements (e.g., contractual data-residency clauses) are known.

## 4. Authentication & Session Model

- Login / logout, forgot/reset password, email verification, session management, optional future 2FA (per FRS §3).
- Recommended: token-based auth (e.g., JWT access token + refresh token) carrying user identity only — **not** the company/tenant ID, which must be re-resolved server-side from membership records on every request (see `05_Security/JWT.md`).
- Platform Super Admin authentication should be architecturally separate from company-user authentication (different login surface/claims), since it is explicitly not a "normal company user."

## 5. API Layer

- Modular API surface aligned to business modules — see `04_API/` for per-module specs (Authentication, CRM, Project, BOQ, Finance, ...).
- Must support versioning (quotations, designs) at the data model level, not just as a UI feature.
- Must support role/permission checks per endpoint, per action (View/Create/Edit/Delete/Approve/Export/Manage/Financial access).

## 6. File/Document Storage

- Needed for: design files (versioned — Design V1/V2/V3, not ad-hoc filenames), drawings, quotation/invoice attachments, expense receipts, handover documents.
- Must associate every stored file with: company (tenant), entity type, entity ID, uploader, timestamp, version (where applicable).

## 7. Audit Logging

- Required for invoices, payments, expenses, quotations, user permissions, project changes.
- Fields: who, what changed, old value, new value, timestamp, entity, entity ID (per FRS §27).
- Should be implemented as an append-only log, separate from the mutable business tables, to survive later data corrections.

## 8. Open Decisions (require client/architect input before build)

1. ~~Backend framework/language and frontend framework~~ — **Resolved, see §2:** React/TypeScript/Vite/Tailwind/shadcn frontend, Django/DRF backend.
2. Multi-tenancy isolation strategy — see §3 above. With Django/DRF confirmed, the leading option is `company_id` on every tenant model enforced via a shared DRF permission class + queryset-manager mixin (defense-in-depth), with Postgres RLS as an optional additional backstop (item 5 below).
3. Hosting/infra provider and deployment model — see `07_DevOps/`.
4. Object storage provider (e.g., S3-compatible, likely via Django's `django-storages`) and retention/versioning policy for design files.
5. Whether Row-Level Security (Postgres RLS) is used as a defense-in-depth layer in addition to application-level tenant scoping (Django ORM does not manage RLS policies natively — would need to be applied via raw migration SQL).
6. Real-time/notification transport (Phase 5) — polling vs. websockets (e.g. Django Channels) vs. push, before WhatsApp/email integration is designed.

## 9. Related Documents

- `02_Architecture/HLD.md` — component-level design
- `02_Architecture/LLD.md` — low-level design (pending API/schema finalization)
- `03_Database/` — schema and naming standards
- `05_Security/` — JWT, tenant isolation, permissions
- `07_DevOps/` — Docker, CI/CD, production deployment
