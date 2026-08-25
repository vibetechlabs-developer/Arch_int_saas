# Folder Structure Standard

**Priority:** Highest — this governs how every other document in this repo maps onto actual code. The confirmed stack is React/TypeScript/Vite (frontend) and Django/DRF (backend) — see `02_Architecture/Technical_Architecture.md` §2. §2 below is the generic/original layering description; §2a gives the concrete Django mapping. The *layering principle* (controller has no business logic, only the repository/manager layer touches raw queries) is non-negotiable regardless of which section's literal names you're reading.

---

## 1. Repository Layout (monorepo)

```
/
├── apps/
│   ├── api/                  # backend application (company + platform APIs)
│   ├── web/                  # company-facing frontend
│   ├── platform-admin/       # Platform Super Admin console (separate app, separate auth surface)
│   └── client-portal/        # Phase 5 — client-facing app
├── packages/
│   ├── shared-types/         # DTOs / API contracts shared between apps
│   ├── ui/                   # shared component library (if web + client-portal share components)
│   └── config/                # shared lint/tsconfig/build config
├── infra/                    # IaC, Docker, CI/CD config — see 07_DevOps/
├── docs/                     # this documentation tree (00_ through 09_)
└── scripts/                  # one-off dev/ops scripts
```

Each app under `apps/` is independently deployable. `platform-admin` is a separate app (not a route inside `web`) because it must never share an auth/session boundary with company users — see `05_Security/JWT.md` §6.

## 2. Backend (`apps/api`) — Module-Per-Business-Entity

The backend is organized **by business module**, mirroring `01_Business/FRS.md`, not by technical layer at the top level:

```
apps/api/src/
├── modules/
│   ├── platform/            # companies, plans, subscriptions, feature flags, platform audit
│   ├── company/              # company profile, settings
│   ├── auth/                 # login, tokens, password reset
│   ├── user/                  # users, company_membership
│   ├── role-permission/      # roles, permissions
│   ├── client/
│   ├── project/
│   ├── product/              # categories, subcategories, products
│   ├── boq/
│   ├── quotation/
│   ├── contract/
│   ├── invoice/
│   ├── payment/
│   ├── expense/
│   ├── report/
│   └── audit-log/
├── shared/
│   ├── middleware/           # tenant-resolution, permission-check — see 05_Security/Tenant.md
│   ├── errors/               # error classes — see Error_Handling.md
│   ├── validation/           # shared schemas/utilities — see Validation_Standards.md
│   └── http/                 # response envelope helpers — see API_Response_Format.md
└── main entrypoint
```

### Inside each module

Every module folder follows the same internal shape, regardless of which module it is:

```
modules/invoice/
├── invoice.routes.ts        # route definitions → controller
├── invoice.controller.ts    # request/response handling only, no business logic
├── invoice.service.ts       # business logic, orchestration
├── invoice.repository.ts    # data access — the ONLY place raw queries for this module live
├── invoice.schema.ts        # request/response validation schemas
├── invoice.types.ts         # module-local types/DTOs
└── invoice.test.ts          # unit/integration tests co-located with the module
```

**Rule:** a controller never talks to the database directly, and a repository never contains business rules. This split exists specifically so tenant-scoping (`company_id` on every query — `05_Security/Tenant.md`) can be enforced in exactly one layer (the repository) and audited there.

## 2a. Backend (`apps/api`) — Concrete Django/DRF Mapping

Django organizes by **app**, which maps 1:1 onto the "module" concept in §2 — one Django app per business module, all living under a common namespace:

```
apps/api/
├── config/                   # Django project settings, urls.py root, wsgi/asgi
├── apps/
│   ├── platform/             # companies, plans, subscriptions, feature flags, platform audit
│   ├── company/
│   ├── authentication/
│   ├── users/                 # User model + CompanyMembership
│   ├── roles_permissions/
│   ├── clients/
│   ├── projects/
│   ├── products/              # categories, subcategories, products
│   ├── boq/
│   ├── quotations/
│   ├── contracts/
│   ├── invoices/
│   ├── payments/
│   ├── expenses/
│   ├── reports/
│   └── audit_log/
├── core/
│   ├── permissions.py         # shared DRF permission classes — tenant + role/permission check
│   ├── exceptions.py           # error classes — see Error_Handling.md
│   ├── validators.py            # shared validation utilities — see Validation_Standards.md
│   ├── pagination.py            # shared response envelope/pagination — see API_Response_Format.md
│   └── managers.py               # tenant-scoped queryset manager mixin (see 05_Security/Tenant.md)
└── manage.py
```

### Inside each Django app (mirrors the generic module shape in §2)

```
apps/invoices/
├── models.py           # ORM models — the ONLY place table structure is defined for this app
├── serializers.py       # DRF serializers — request/response shape, maps to *.schema.ts equivalent
├── views.py              # DRF ViewSets/APIViews — request/response handling only, no business logic
├── services.py            # business logic, orchestration (the equivalent of *.service.ts)
├── permissions.py          # app-specific DRF permission classes, composed with core/permissions.py
├── urls.py                  # route registration
├── migrations/                # Django-generated, sequenced per 03_Database/Migration_Plan.md
└── tests/
```

**Django-specific rule, same intent as §2's repository rule:** a DRF view/ViewSet never contains business logic and never issues raw queries beyond what a model manager exposes — business logic lives in `services.py`, and every queryset for a tenant-owned model goes through the tenant-scoped manager mixin in `core/managers.py`, never a bare `Model.objects.filter(...)` that forgets `company_id`. This is where `05_Security/Tenant.md`'s "query layer" enforcement point is implemented concretely.

## 3. Frontend (`apps/web`) — Feature-Based

```
apps/web/src/
├── features/
│   ├── dashboard/
│   ├── clients/
│   ├── projects/
│   ├── boq/
│   ├── quotations/
│   ├── invoices/
│   ├── payments/
│   ├── expenses/
│   ├── reports/
│   └── settings/
├── components/                # shared, feature-agnostic UI components
├── hooks/                     # shared hooks
├── lib/                        # API client, auth context, permission-check helpers
└── routes/                     # route tree, wired to permission-gated layouts
```

Each `features/<name>/` folder is self-contained: its own components, API calls, and local state. Cross-feature reuse goes through `components/`, `hooks/`, or `lib/` — never a direct import from one feature into another's internals.

## 4. What Must Never Happen

- No business logic in a controller/route handler.
- No raw SQL/query outside a `*.repository.ts` (or ORM-equivalent) file.
- No frontend feature importing directly from another feature's folder.
- No module bypassing `shared/middleware` — every route is registered through the tenant/permission middleware pipeline, with zero exceptions for "internal" or "trusted" endpoints.

## 5. Phase Alignment

Only build module folders for the current roadmap phase (`09_Project/Roadmap.md`). Do not scaffold Phase 3–5 module folders (`lead/`, `site-visit/`, `design/`, `procurement/`, ...) until that phase is actually scheduled — an empty folder structure for unbuilt features invites half-finished code.
