# BACKEND_TASKS.md

## Setup Audit — 2026-08-25

A full setup audit was run against the actual codebase (not just this file). Findings and fixes, beyond the per-task status corrections below:

- **Real bug, fixed:** `apps/authentication/authentication.py`'s `TenantJWTAuthentication` determined `is_platform_admin` from a custom `user_type` token claim that isn't guaranteed to be present (only set by `PlatformAdminRefreshToken.for_user()`, not by `PlatformAdminAccessToken.for_user()` called directly). Switched to the SimpleJWT-native `token_type` claim, matching `apps/users/permissions.py::is_platform_admin()`. This was silently sending real platform-admin tokens down the regular-company-user tenant-resolution path.
- **Real bug, fixed:** a user authenticated but with zero active company memberships was raising 401 `AuthenticationFailed` instead of 403 `PermissionDenied` — contradicted `00_Development_Standards/Error_Handling.md`'s own `PermissionError` definition ("authenticated, but not authorized").
- **Real bug, fixed:** `apps/common/exceptions.py`'s `EXCEPTION_MAP` mapped DRF's `PermissionDenied` to code `FORBIDDEN` while Django's `PermissionDenied` mapped to `PERMISSION_ERROR` for the same 403 case — unified to `PERMISSION_ERROR` per the doc's single `PermissionError` category.
- Deleted a dead, never-imported duplicate `Role` model at `apps/users/models/role.py` (an orphaned directory alongside `models.py`, no `__init__.py`, silently shadowed).
- Moved the tenant-info diagnostic endpoint out of the production URLconf (`apps/users/urls.py`) into a test-only URLconf (`apps/users/tests/tenant_info_support.py`) used solely by `test_tenant_auth_integration.py`.
- Introduced `repositories.py` + `validators.py` (+ `selectors.py` where a list endpoint exists) in `apps.company`, `apps.users`, and `apps.authentication`, per `BACKEND_RULES.md`'s View→Serializer→Service→Repository→Model rule. `apps.common` was left as-is — it has no services/views/urls of its own (shared abstractions only), so the module-file rule doesn't apply to it as written.
- Initialized git (`chore/initial-backend-baseline` branch — see repo root `.gitignore`); `main` intentionally has no commits yet per `Git_Strategy.md`'s no-direct-commit rule, pending the first PR merge.
- Created `backend/.env` (gitignored) from `.env.example` so local dev/test runs work without manual setup.

Before this audit's fixes: 19 genuine failures (401/403 mismatches) out of 195 tests, isolated to the two bugs above. Full suite re-verified green after fixes and after the repository-layer refactor: **195 passed, 0 failed** (`pytest -q`, 2026-08-25).

## Purpose

This document is the **single source of truth** for backend development progress.

It tracks every backend engineering task, its status, ownership, dependencies, priority, and completion. Every Claude Code session must read this file before starting work.

---

# Rules

- Never start a task marked **Blocked**.
- Always complete dependencies before starting a new task.
- Work only on **one task at a time** unless explicitly instructed.
- Update the task status immediately after completion.
- Never skip task numbering.
- If a task requires architectural clarification, stop and ask instead of making assumptions.

---

# Task Status

| Status | Meaning |
|----------|---------|
| Todo | Task has not started |
| In Progress | Currently being implemented |
| Review | Awaiting code review |
| Testing | Under QA/testing |
| Done | Completed and approved |
| Blocked | Waiting on dependency |

---

# Sprint 1 – Backend Foundation

## Epic 1 – Project Setup

### BE-001 – Initialize Django Project

**Status:** Review

**Priority:** Critical

**Owner:** Backend Team

**Implementation notes:** Django 5.2 LTS (pinned `>=5.2,<5.3`, confirmed by user — undocumented elsewhere), isolated venv at `backend/.venv/`, standard `django-admin startproject config .` layout, `manage.py check` passes clean. No settings customization, no apps, no dependencies beyond Django itself — those are BE-002/BE-003/BE-004+.

---

### BE-002 – Configure Project Settings

**Status:** Review

**Priority:** Critical

**Owner:** Backend Team

**Implementation notes:** Single `config/settings.py`, env-var driven (stdlib `os.environ`, no third-party package — `django-environ` is BE-003). `SECRET_KEY`/`DEBUG`/`ALLOWED_HOSTS` env-driven, `DEBUG` defaults `False`. `DATABASES` configured for PostgreSQL per `02_Architecture/Technical_Architecture.md`, env-driven, defaults matching `07_DevOps/Docker.md`. `STATIC_ROOT`/`MEDIA_ROOT` added. Baseline `LOGGING` (structured JSON with requestId/companyId deferred until request-context middleware exists — BE-005/006/015). Production-only security hardening block gated on `DEBUG=False`. `backend/.env.example` created.

**Known open item (accepted, not a defect):** `manage.py check` currently fails with `ModuleNotFoundError: psycopg` — the PostgreSQL backend requires the `psycopg` driver, which is a BE-003 dependency not yet installed. Confirmed by the user this is expected and acceptable for BE-002; resolves automatically once BE-003 installs `psycopg`. No dependency was installed to work around this.

---

### BE-003 – Install Core Dependencies

**Status:** Review

**Priority:** Critical

**Owner:** Backend Team

**Implementation notes:** Installed core packages (Django REST Framework, SimpleJWT, drf-spectacular, django-filter, Pillow, psycopg[binary], django-environ, django-cors-headers, redis, celery) into `backend/.venv/`. Structured requirements files into `backend/requirements/` (`base.txt`, `dev.txt`, `prod.txt`). Configured `backend/config/settings.py` with `django-environ`, DRF defaults, JWT settings, drf-spectacular OpenAPI configuration, CORS headers middleware/origins, and Celery settings. Celery application initialized in `backend/config/celery.py` and `backend/config/__init__.py`. `backend/.env.example` updated with CORS, Celery, and Redis configuration variables. `python manage.py check` passes with 0 issues. Clean install test from `requirements/base.txt` verified.

Dependencies:

- Django REST Framework
- SimpleJWT
- drf-spectacular
- django-filter
- Pillow
- psycopg
- django-environ
- django-cors-headers
- Redis
- Celery

---

## Epic 2 – Common Module

### BE-004 – Create Common App

**Status:** Done

**Priority:** Critical

**Owner:** Backend Team

**Implementation notes:** Created `apps.common` app (`backend/apps/common/`) containing the core model abstractions: `UUIDModel`, `TimeStampedModel`, `SoftDeleteModel`, and `BaseModel`. Implemented `SoftDeleteQuerySet`, `SoftDeleteManager`, `SoftDeleteAllManager`, and `SoftDeleteDeletedManager` in `backend/apps/common/managers.py` supporting soft-delete (`deleted_at`), query filtering, `restore()`, and `hard_delete()`. Added `apps.common` to `INSTALLED_APPS`. Created comprehensive test suite in `backend/apps/common/tests/test_models.py` covering UUID generation/PK behavior, timestamp auto-assignment and updates, soft-delete lifecycle, manager filtering, restore, hard deletion, and abstract model inheritance (all 11 tests pass in pytest and manage.py test). Code review completed and APPROVED.

Dependencies:

- BE-001
- BE-002

Acceptance Criteria

- BaseModel
- UUIDModel
- TimeStampedModel
- SoftDeleteModel

---

### BE-005 – Global API Response

**Status:** Review

**Priority:** Critical

**Owner:** Backend Team

**Implementation notes:** *(Backfilled — this task was already implemented but left tracked as Todo; corrected during setup audit on 2026-08-25.)* Implemented `ApiResponse` in `apps/common/responses.py` — `success()`, `created()`, `error()`, `paginated()`, `no_content()` classmethods enforcing the standard `{success, data, requestId}` / `{success, error, requestId}` envelope and mandatory `X-Request-ID` response header. `request_id` sourced from `RequestIDMiddleware` (`apps/common/middleware.py`), which validates/generates a `req_<12 hex>` ID per request. Used consistently across `apps.authentication`, `apps.company`, and `apps.users` views.

Depends On

- BE-004

---

### BE-006 – Global Exception Handler

**Status:** Review

**Priority:** Critical

**Owner:** Backend Team

**Implementation notes:** *(Backfilled — already implemented but left tracked as Todo; corrected during setup audit on 2026-08-25.)* Implemented `custom_exception_handler` in `apps/common/exceptions.py`, registered as `REST_FRAMEWORK["EXCEPTION_HANDLER"]`. Maps ~15 DRF/Django exception types (validation, auth, permission, not-found, conflict, business-rule, throttling, upstream service errors) to the standard error envelope via `ApiResponse.error()`, with a validation-detail flattener, 5xx logged at ERROR with stack trace / 4xx at WARNING, and a safety net so a handler crash never surfaces as a raw 500. Adds reusable `ConflictError`, `BusinessRuleError`, `ExternalServiceError` exception classes for domain code to raise.

Depends On

- BE-005

---

## Epic 3 – Authentication

### BE-007 – Custom User Model

**Status:** Review

**Priority:** Critical

**Owner:** Backend Team

**Implementation notes:** *(Backfilled — already implemented but left tracked as Todo, which was inconsistent with BE-008/010/011 already being in Review despite depending on it; corrected during setup audit on 2026-08-25.)* Implemented in `apps/users/models.py` (not a dedicated `accounts`/`authentication` app — lives in `apps.users`): `User` (extends `AbstractBaseUser`, `PermissionsMixin`, `BaseModel`; email as `USERNAME_FIELD`; UUID PK; soft-delete-aware `status` property) and `CompanyMembership` (join model linking `User` ↔ `Company`, with `CompanyMembershipStatus` choices `active`/`invited`/`revoked` and a unique-active-membership-per-company-per-user constraint). `AUTH_USER_MODEL = "users.User"`. Custom `UserManager` in `apps/users/managers.py`. Covered by `apps/users/tests/test_models.py`, `test_serializers.py`, `test_membership.py`.

Depends On

- BE-004

---

### BE-008 – JWT Authentication

**Status:** Review

**Priority:** Critical

**Owner:** Backend Team

**Implementation notes:** Implemented JWT-based authentication module (`apps.authentication`) using `djangorestframework-simplejwt`. Created company user login (`/auth/login`), token refresh with rotation (`/auth/refresh`), logout with token blacklisting (`/auth/logout`), current user lookup (`/auth/me`), and platform super admin login (`/platform-auth/login`). Configured custom token classes (`CompanyUserRefreshToken`, `PlatformAdminRefreshToken`, `CompanyUserAccessToken`, `PlatformAdminAccessToken`) enforcing token claim boundaries (`sub`, `email`, `token_type`, strictly omitting company/tenant and role claims). Integrated with `ApiResponse` (`BE-005`), `custom_exception_handler` (`BE-006`), and custom `User` model (`BE-007`). Added `rest_framework_simplejwt.token_blacklist` and `apps.authentication` to `INSTALLED_APPS`. Implemented 24 test cases in `apps/authentication/tests/` covering login, token claims, email normalization, inactive/deleted user rejection, token refresh, rotation & blacklisting, logout, `/auth/me`, and platform super admin authentication. All 91 backend tests pass 100% in pytest and manage.py test.

Depends On

- BE-007

Acceptance Criteria

- JWT access/refresh token generation
- Token rotation & blacklist revocation
- Company user login & platform super admin login
- Current user profile endpoint (`/auth/me`)
- Standard API response envelope & exception integration
- Complete test suite coverage

### BE-009 – Password Reset

**Status:** Review

**Priority:** Critical

**Owner:** Backend Team

**Implementation notes:** Implemented secure password reset workflow in `apps.authentication`. Created `PasswordResetToken` model with SHA-256 token hashing, 1-hour expiration, and single-use consumption state. Implemented `POST /auth/forgot-password` with email normalization and complete user enumeration prevention (returns identical generic success message whether email exists, does not exist, is inactive, or is soft-deleted). Created `PasswordResetEmailService` with configurable frontend URL. Implemented `POST /auth/reset-password` supporting token validation, expiration check, consumption check, Django password validators compliance, atomic password update, token consumption, and automatic invalidation/blacklisting of all existing active sessions/refresh tokens for the user. Added 17 dedicated test cases in `apps/authentication/tests/test_forgot_password.py` and `test_reset_password.py`. All 108 backend tests pass 100% in pytest and manage.py test.

Depends On

- BE-008

Acceptance Criteria

- PasswordResetToken model with SHA-256 digest storage
- POST /auth/forgot-password with user enumeration defense
- POST /auth/reset-password with Django password validation
- Atomic password update and active session invalidation
- Complete test suite coverage

---

## Epic 4 – Company

### BE-010 – Company Model

**Status:** Review

**Priority:** Critical

**Owner:** Backend Team

**Implementation notes:** Implemented `Company` model in `apps.company`. Extends `apps.common.models.BaseModel` (`UUIDModel`, `TimeStampedModel`, `SoftDeleteModel`). Configured `CompanyStatus` choices (`trial`, `active`, `suspended`), currency (default `INR`), optional `gst_number`, JSON `settings` dictionary, and database table `company` with indexes on `created_at`, `deleted_at`, and `status`. Registered `apps.company` in `INSTALLED_APPS` and registered `Company` in Django admin. Created `CompanySerializer` with camelCase JSON fields. Generated initial migration `apps/company/migrations/0001_initial.py`. Added 9 unit tests in `apps/company/tests/test_models.py` and `test_serializers.py`. All 117 backend tests pass 100% in pytest and manage.py test.

Depends On

- BE-007

Acceptance Criteria

- Company model inheriting from BaseModel (UUID, TimeStamped, SoftDelete)
- CompanyStatus choices (trial, active, suspended)
- Default INR currency and optional GSTIN
- JSON settings field with default structure
- Django Admin registration
- Comprehensive test coverage for model and serializer

---

### BE-011 – Company CRUD

**Status:** Review

**Priority:** Critical

**Owner:** Backend Team

**Implementation notes:** Implemented Company CRUD endpoints and service layer in `apps.company`. Created `CompanyService` encapsulating company creation, retrieval, listing with search/status filters, partial updates, and soft deletion. Implemented `CompanySerializer`, `CompanyCreateSerializer`, and `CompanyUpdateSerializer` in `apps/company/serializers.py`. Created `CompanyViewSet` in `apps/company/views.py` backed by `IsPlatformAdminOrCompanyAccess` permissions, standard pagination, and `ApiResponse` envelopes. Registered `/companies` routes in `apps/company/urls.py` and included in `config/urls.py`. Added comprehensive unit and integration test coverage across `apps/company/tests/test_services.py` and `apps/company/tests/test_views.py`. All 147 backend tests pass 100% in pytest and manage.py test.

Depends On

- BE-010

Acceptance Criteria

- Full CRUD endpoints (/companies, /companies/{id}) with camelCase schema
- Platform Admin permissions for create, list, and soft-delete
- Company member permissions for retrieve and update of own tenant
- Service layer (CompanyService) handling all business logic
- Standard pagination and status filtering/search
- 100% test coverage and zero regressions

---

## Epic 5 – RBAC

### BE-012 – Role Model

**Status:** Review

**Priority:** Critical

**Owner:** Backend Team

**Implementation notes:** *(Backfilled — already implemented but left tracked as Todo; corrected during setup audit on 2026-08-25.)* Implemented `Role` in `apps/users/models.py`: extends `BaseModel` (UUID, TimeStamped, SoftDelete), `company` FK (tenant-scoped, `related_name="roles"`), `name`, `description`, `is_active`, unique-active-role-per-company constraint. Note: an earlier duplicate copy at `apps/users/models/role.py` (an orphaned, never-imported directory alongside `models.py`) was found dead and deleted during the audit — it was not wired into any import path.

Depends On

- BE-007
- BE-010

---

### BE-013 – Permission System

**Status:** Review

**Priority:** Critical

**Owner:** Backend Team

**Implementation notes:** *(Backfilled — already implemented but left tracked as Todo; corrected during setup audit on 2026-08-25.)* Implemented in `apps/users/permissions.py`: `is_platform_admin()` (checks Django superuser flag or `platform_admin` JWT token claim, fails closed), `has_permission()` (platform admins universal; company users require active, non-deleted `CompanyMembership`, optionally scoped to a specific company), and `RolePermission` (DRF permission class enforcing tenant-scoped object-level access for Role endpoints).

Depends On

- BE-012

---

### BE-014 – Role CRUD

**Status:** Review

**Priority:** Critical

**Owner:** Backend Team

**Implementation notes:** *(Backfilled — already implemented but left tracked as Todo; corrected during setup audit on 2026-08-25.)* Implemented `RoleViewSet` in `apps/users/views.py` (list/create/retrieve/partial_update/update/destroy — full CRUD, soft-delete on destroy), `RoleSerializer`/`RoleCreateSerializer`/`RoleUpdateSerializer` in `apps/users/serializers.py`, `RoleService` in `apps/users/services.py`. Routes at `/roles`, `/roles/{id}` in `apps/users/urls.py`. Platform admins can target any company via `companyId`; regular users are restricted to companies where they hold active membership. drf-spectacular schema annotations included. Covered by `apps/users/tests/test_role_views.py`, `test_role_permissions.py`, `test_role_services.py`, `test_role_serializers.py`.

Depends On

- BE-013

---

## Epic 6 – Multi-Tenant

### BE-015 – Tenant Middleware

**Status:** Review

**Priority:** Critical

**Owner:** Backend Team

**Implementation notes:** *(Backfilled — already implemented but left tracked as Todo; corrected during setup audit on 2026-08-25.)* Implemented as a custom DRF authentication class, `TenantJWTAuthentication` in `apps/authentication/authentication.py`, rather than Django middleware — task title kept as-is for traceability, but the mechanism differs from the original "Tenant Middleware" framing. Registered as the sole `DEFAULT_AUTHENTICATION_CLASSES`. After standard JWT validation, resolves `request.company_id` and `request.is_platform_admin`: platform-admin tokens bypass tenant resolution; company-user tokens resolve tenant from active `CompanyMembership` records, requiring an explicit `companyId` (validated against real active memberships, never trusted blindly) when a user belongs to more than one company, and rejecting requests with no active membership. `/auth/logout`, `/auth/me`, `/auth/refresh` are exempted from tenant resolution. Integration-tested end-to-end (10 scenarios: single/multi membership, revoked/soft-deleted membership, platform admin, unauthenticated, invalid JWT) via `apps/users/tests/test_tenant_auth_integration.py`, using a test-only URLconf/view (`apps/users/tests/tenant_info_support.py`) so the diagnostic endpoint doesn't ship in production routes.

Depends On

- BE-010
- BE-012

---

## Epic 7 – API Documentation

### BE-016 – Swagger Configuration

**Status:** Review

**Priority:** Critical

**Owner:** Backend Team

**Implementation notes:** Wired up OpenAPI schema + interactive docs in `config/urls.py`: `GET /schema/` (raw OpenAPI 3.0.3 document, `SpectacularAPIView`), `GET /docs/` (Swagger UI, `SpectacularSwaggerView`), `GET /redoc/` (ReDoc, `SpectacularRedocView`) — unprefixed, matching every other route in this project (`API_Response_Format.md` §6, unversioned by default). All three are `permission_classes=[AllowAny]` — the schema only describes endpoint shapes, never tenant data, and gating it behind auth would block onboarding for anyone without a token yet.

Registered `apps/authentication/schema.py`'s `TenantJWTAuthenticationScheme` (an `OpenApiAuthenticationExtension`) via `AuthenticationConfig.ready()` in `apps/authentication/apps.py`, so `TenantJWTAuthentication` resolves to a proper `bearer`/`JWT` security scheme in the generated docs instead of leaving every authenticated endpoint's auth type unresolved.

Fixed the two `GenericViewSet`-based views (`CompanyViewSet`, `RoleViewSet`) that fully override every action and never call `self.get_queryset()`/`self.get_object()` — added a `queryset = Model.objects.none()` class attribute to each (inert at runtime, confirmed by the full test suite; exists solely so drf-spectacular can resolve the response model for introspection).

Per-endpoint `@extend_schema`/`@extend_schema_view` annotations (summary, description, request/response serializers, tags) were already present across `apps.authentication`, `apps.company`, and `apps.users` views from earlier tasks — no gaps found there.

Verified via `manage.py spectacular --fail-on-warn`: 0 errors, 0 warnings (previously 21 warnings / 11 unique, all resolved by the two fixes above).

**Self-review finding, fixed:** DRF's `APIView.initial()` calls `perform_authentication()` unconditionally, so `TenantJWTAuthentication` runs on every request regardless of a view's `permission_classes`. `/schema/`, `/docs/`, `/redoc/` weren't in its `exempt_paths` list, so a caller with a stored Bearer token but no (or ambiguous) company membership would get 403 just from loading the docs — added the three paths to `exempt_paths` in `apps/authentication/authentication.py`. (Noted but intentionally not touched: the pre-existing `/auth/logout`, `/auth/me`, `/auth/refresh` entries in that same list have no trailing slash while their routes allow an optional one, so a request to `/auth/logout/` wouldn't actually match the exemption — out of scope for BE-016, flagged for a future task.)

Added `apps/common/tests/test_api_docs.py` (6 tests): schema is public and parses as valid OpenAPI 3.0.3 naming this project, the `TenantJWTAuth` bearer/JWT scheme is present, known endpoints (`/auth/login/`, `/auth/me/`, `/companies/`, `/roles/`) resolve into the schema, `/docs/` and `/redoc/` render without authentication, and all three routes stay reachable for a caller holding a valid token with no company membership (regression test for the self-review fix above). Full backend suite re-verified green after this change: **201 passed, 0 failed**.

Depends On

- BE-008

---

## Epic 8 – Testing

### BE-017 – Authentication Tests

**Status:** Todo

Depends On

- BE-008

---

### BE-018 – Company Tests

**Status:** Todo

Depends On

- BE-011

---

## Epic 9 – Audit

### BE-019 – Audit Log

**Status:** Todo

Depends On

- BE-004

---

## Epic 10 – Infrastructure

### BE-020 – Docker & Docker Compose

**Status:** Todo

Depends On

- BE-001

---

# Sprint 2 – CRM

- BE-021 – Client Module
- BE-022 – Client CRUD
- BE-023 – Project Module
- BE-024 – Project Members
- BE-025 – Project Workflow
- BE-026 – Project Filters
- BE-027 – Project Audit Logs
- BE-028 – CRM Tests

Status: Todo

---

# Sprint 3 – Product Catalog

- BE-029 – Categories
- BE-030 – Subcategories
- BE-031 – Products
- BE-032 – Units
- BE-033 – Catalog APIs

Status: Todo

---

# Sprint 4 – BOQ

- BE-034 – BOQ Module
- BE-035 – BOQ Items
- BE-036 – BOQ Calculations
- BE-037 – BOQ APIs

Status: Todo

---

# Sprint 5 – Quotation

- BE-038 – Quotation
- BE-039 – Versioning
- BE-040 – Approval Workflow

Status: Todo

---

# Sprint 6 – Finance

- BE-041 – Invoice
- BE-042 – Payment
- BE-043 – Expense
- BE-044 – Financial Reports

Status: Todo

---

# Sprint 7 – Platform

- Notifications
- Documents
- Activity Logs
- Dashboard
- Analytics

Status: Todo

---

# Backend Lead Workflow

Before starting any task:

1. Read `CLAUDE.md`
2. Read `BACKEND_RULES.md`
3. Read `BACKEND_ROADMAP.md`
4. Read this file (`BACKEND_TASKS.md`)
5. Select the first task with **Status: Todo** whose dependencies are complete.
6. Explain the implementation plan.
7. Implement only that task.
8. Update the task status to **Review** when complete.
9. Wait for code review before moving to the next task.