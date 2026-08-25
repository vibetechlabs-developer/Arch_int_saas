# Naming Conventions

**Priority:** Highest. Database-specific naming (tables/columns) is defined authoritatively in `03_Database/Naming_Standards.md` — this document covers everything else and must stay consistent with it.

---

## 1. Files & Folders

| Type | Convention | Example |
|---|---|---|
| Folders | `kebab-case` | `role-permission/`, `client-portal/` |
| Backend module files | `kebab-case`, suffixed by layer | `invoice.service.ts`, `invoice.repository.ts` |
| Frontend component files | `PascalCase` matching the component name | `ClientDetailPage.tsx`, `InvoiceStatusBadge.tsx` |
| Frontend non-component files | `camelCase` | `useProjectCost.ts`, `apiClient.ts` |
| Test files | mirror the file under test + `.test.` / `.spec.` | `invoice.service.test.ts` |
| Config files | lowercase, tool-standard names | `tsconfig.json`, `.eslintrc.json` |

## 2. Code-Level Naming

| Element | Convention | Example |
|---|---|---|
| Variables, functions | `camelCase` | `calculateProjectCost()`, `pendingAmount` |
| Classes, interfaces, types, React components | `PascalCase` | `InvoiceService`, `ProjectStatus`, `ClientCard` |
| Constants (truly immutable, module-level) | `UPPER_SNAKE_CASE` | `MAX_QUOTATION_VERSIONS`, `DEFAULT_TAX_RATE` |
| Enum members | `PascalCase` for the enum type, `UPPER_SNAKE_CASE` or `PascalCase` members (pick one per codebase and stay consistent) | `enum InvoiceStatus { Draft, Sent, PartiallyPaid, Paid, Overdue, Cancelled }` |
| Booleans | prefixed `is`/`has`/`can`/`should` | `isActive`, `hasOutstandingBalance`, `canApprove` |
| Functions returning booleans | same prefix rule as booleans | `isProjectOverdue()`, `canUserApproveQuotation()` |
| Async functions | no special prefix, but always return a `Promise` explicitly typed | `async function getInvoiceById(id: string): Promise<Invoice>` |
| Private/internal-only members | prefixed `_` only if the language has no native `private` keyword; otherwise use the language's real access modifier | — |

## 3. Domain Terminology — Use Business Language Consistently

Names in code must match the business vocabulary from `01_Business/FRS.md` exactly — do not invent synonyms. This keeps code, API, database, and documentation searchable as one vocabulary.

| Use | Not |
|---|---|
| `Quotation` | `Quote`, `Estimate` |
| `BOQ` / `BillOfQuantities` | `WorkOrder`, `Scope` |
| `Expense` | `Cost` (as an entity name — "cost" is fine as a computed value, e.g. `projectCost`) |
| `CompanyMembership` | `UserCompany`, `TenantUser` |
| `Company` (tenant) | `Tenant`, `Organization`, `Account` — pick **one** term platform-wide (this project uses "Company" per the source requirements) and never mix in a synonym |

## 4. API Routes

- `kebab-case`, plural nouns for collections: `/companies/{companyId}/purchase-orders`, not `/purchaseOrder` or `/purchase_order`.
- Nested resources reflect real ownership: `/companies/{companyId}/projects/{projectId}/boq/items/{itemId}`, not a flat `/boq-items/{itemId}` with an implicit project.
- Actions that aren't pure CRUD are verbs at the end of the path: `POST /quotations/{id}/approve`, `POST /invoices/{id}/send` — never a generic `PATCH` with a `status` field for an action that has business meaning (approval, sending, cancellation), because actions need their own audit-log semantics (see `Error_Handling.md` and `05_Security/Tenant.md`).

## 5. Environment Variables

- `UPPER_SNAKE_CASE`, namespaced by concern: `DATABASE_URL`, `JWT_ACCESS_SECRET`, `OBJECT_STORAGE_BUCKET`.
- Never a bare secret name that could collide across services (e.g. not `SECRET`, use `AUTH_JWT_SECRET`).

## 6. Permission Codes

Per `05_Security/Permissions.md`: `<module>.<action>`, lowercase, dot-separated — `invoice.view`, `expense.approve`, `report.financial_access`. Module names here must match the backend module folder names in `Folder_Structure.md` exactly.

## 7. Language-Specific Naming: Python/Django Backend vs. TypeScript/React Frontend

With the stack confirmed as Django/DRF (backend) and React/TypeScript (frontend) — `02_Architecture/Technical_Architecture.md` §2 — the two sides of the codebase follow **their own language's native convention** rather than forcing one style across the stack boundary. This is a deliberate exception to "one vocabulary" in §3 (which governs *domain terms*, not *casing*):

| Element | Backend (Python/Django, PEP 8) | Frontend (TypeScript/React) |
|---|---|---|
| Files/modules | `snake_case.py` (`services.py`, `invoice_status.py`) | `kebab-case`/`PascalCase` per §1 |
| Functions, variables | `snake_case` (`calculate_project_cost`, `pending_amount`) | `camelCase` per §2 |
| Classes (models, serializers, services) | `PascalCase` (`InvoiceService`, `ProjectStatus`) | `PascalCase` per §2 — same rule, same result |
| Constants | `UPPER_SNAKE_CASE` (`MAX_QUOTATION_VERSIONS`) | `UPPER_SNAKE_CASE` per §2 — same rule |
| Django app names | `snake_case`, plural where Django convention expects it (`invoices`, `boq`) | n/a |

**The translation boundary is the API response layer** (`00_Development_Standards/API_Response_Format.md` §5): DRF serializers output `camelCase` JSON fields even though the underlying Python/model attributes are `snake_case` — the frontend never sees a `snake_case` field name, and the database columns stay `snake_case` per `03_Database/Naming_Standards.md`. Three different casing conventions across DB → backend → API-response → frontend is correct and expected here, as long as each layer is internally consistent and the serializer is where the conversion happens — not scattered `camelCase`/`snake_case` mixing within one layer.

## 8. Git Branches, Commits

See `Branch_Naming.md` and `Commit_Message_Format.md` — both follow their own stricter, tool-enforced conventions layered on top of the rules above.

## 9. Anti-Patterns to Reject in Review

- Abbreviations that aren't universally obvious (`qty` is fine, `qt` is not; `amt` should just be `amount`).
- Hungarian notation (`strName`, `bIsActive`) — the type system/language convention already communicates type.
- Generic names for domain entities (`data`, `item`, `obj`, `temp`) anywhere outside a genuinely generic utility function.
- Mixing naming conventions for the same concept across backend/frontend (e.g. backend `company_id`, frontend `companyId` is fine — that's a language convention difference; but `company_id` vs `tenantId` for the *same field* is not).
