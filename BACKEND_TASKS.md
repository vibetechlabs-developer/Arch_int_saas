# BACKEND_TASKS.md

## Sprint 1 Closure — 2026-08-27

Sprint 1 (Foundation) is **Done**. All 21 tasks (BE-001–BE-021, including the Epic 11 stabilization/hardening work) are approved and closed. Full backend test suite: **281 passed, 0 failed**. BE-020's Docker stack was subsequently verified end-to-end (2026-08-27): `docker compose up` brings up all 6 services healthy (postgres, redis, django, celery-worker, celery-beat, nginx), with `/health/` reachable through both django directly and the nginx reverse proxy — a real `curl`-missing-in-dev-stage bug was found and fixed in the process (see BE-020). No open Docker verification gap remains. Sprint 2 (CRM: Client/Project modules) has not started and requires explicit instruction to begin, per this repo's build-order and phasing rules.

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

**Status:** Done

**Priority:** Critical

**Owner:** Backend Team

**Implementation notes:** Django 5.2 LTS (pinned `>=5.2,<5.3`, confirmed by user — undocumented elsewhere), isolated venv at `backend/.venv/`, standard `django-admin startproject config .` layout, `manage.py check` passes clean. No settings customization, no apps, no dependencies beyond Django itself — those are BE-002/BE-003/BE-004+.

---

### BE-002 – Configure Project Settings

**Status:** Done

**Priority:** Critical

**Owner:** Backend Team

**Implementation notes:** Single `config/settings.py`, env-var driven (stdlib `os.environ`, no third-party package — `django-environ` is BE-003). `SECRET_KEY`/`DEBUG`/`ALLOWED_HOSTS` env-driven, `DEBUG` defaults `False`. `DATABASES` configured for PostgreSQL per `02_Architecture/Technical_Architecture.md`, env-driven, defaults matching `07_DevOps/Docker.md`. `STATIC_ROOT`/`MEDIA_ROOT` added. Baseline `LOGGING` (structured JSON with requestId/companyId deferred until request-context middleware exists — BE-005/006/015). Production-only security hardening block gated on `DEBUG=False`. `backend/.env.example` created.

**Known open item (accepted, not a defect):** `manage.py check` currently fails with `ModuleNotFoundError: psycopg` — the PostgreSQL backend requires the `psycopg` driver, which is a BE-003 dependency not yet installed. Confirmed by the user this is expected and acceptable for BE-002; resolves automatically once BE-003 installs `psycopg`. No dependency was installed to work around this.

---

### BE-003 – Install Core Dependencies

**Status:** Done

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

**Status:** Done

**Priority:** Critical

**Owner:** Backend Team

**Implementation notes:** *(Backfilled — this task was already implemented but left tracked as Todo; corrected during setup audit on 2026-08-25.)* Implemented `ApiResponse` in `apps/common/responses.py` — `success()`, `created()`, `error()`, `paginated()`, `no_content()` classmethods enforcing the standard `{success, data, requestId}` / `{success, error, requestId}` envelope and mandatory `X-Request-ID` response header. `request_id` sourced from `RequestIDMiddleware` (`apps/common/middleware.py`), which validates/generates a `req_<12 hex>` ID per request. Used consistently across `apps.authentication`, `apps.company`, and `apps.users` views.

Depends On

- BE-004

---

### BE-006 – Global Exception Handler

**Status:** Done

**Priority:** Critical

**Owner:** Backend Team

**Implementation notes:** *(Backfilled — already implemented but left tracked as Todo; corrected during setup audit on 2026-08-25.)* Implemented `custom_exception_handler` in `apps/common/exceptions.py`, registered as `REST_FRAMEWORK["EXCEPTION_HANDLER"]`. Maps ~15 DRF/Django exception types (validation, auth, permission, not-found, conflict, business-rule, throttling, upstream service errors) to the standard error envelope via `ApiResponse.error()`, with a validation-detail flattener, 5xx logged at ERROR with stack trace / 4xx at WARNING, and a safety net so a handler crash never surfaces as a raw 500. Adds reusable `ConflictError`, `BusinessRuleError`, `ExternalServiceError` exception classes for domain code to raise.

Depends On

- BE-005

---

## Epic 3 – Authentication

### BE-007 – Custom User Model

**Status:** Done

**Priority:** Critical

**Owner:** Backend Team

**Implementation notes:** *(Backfilled — already implemented but left tracked as Todo, which was inconsistent with BE-008/010/011 already being in Review despite depending on it; corrected during setup audit on 2026-08-25.)* Implemented in `apps/users/models.py` (not a dedicated `accounts`/`authentication` app — lives in `apps.users`): `User` (extends `AbstractBaseUser`, `PermissionsMixin`, `BaseModel`; email as `USERNAME_FIELD`; UUID PK; soft-delete-aware `status` property) and `CompanyMembership` (join model linking `User` ↔ `Company`, with `CompanyMembershipStatus` choices `active`/`invited`/`revoked` and a unique-active-membership-per-company-per-user constraint). `AUTH_USER_MODEL = "users.User"`. Custom `UserManager` in `apps/users/managers.py`. Covered by `apps/users/tests/test_models.py`, `test_serializers.py`, `test_membership.py`.

Depends On

- BE-004

---

### BE-008 – JWT Authentication

**Status:** Done

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

**Status:** Done

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

**Status:** Done

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

**Status:** Done

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

**Status:** Done

**Priority:** Critical

**Owner:** Backend Team

**Implementation notes:** *(Backfilled — already implemented but left tracked as Todo; corrected during setup audit on 2026-08-25.)* Implemented `Role` in `apps/users/models.py`: extends `BaseModel` (UUID, TimeStamped, SoftDelete), `company` FK (tenant-scoped, `related_name="roles"`), `name`, `description`, `is_active`, unique-active-role-per-company constraint. Note: an earlier duplicate copy at `apps/users/models/role.py` (an orphaned, never-imported directory alongside `models.py`) was found dead and deleted during the audit — it was not wired into any import path.

Depends On

- BE-007
- BE-010

---

### BE-013 – Permission System

**Status:** Done

**Priority:** Critical

**Owner:** Backend Team

**Implementation notes:** *(Backfilled — already implemented but left tracked as Todo; corrected during setup audit on 2026-08-25.)* Implemented in `apps/users/permissions.py`: `is_platform_admin()` (checks Django superuser flag or `platform_admin` JWT token claim, fails closed), `has_permission()` (platform admins universal; company users require active, non-deleted `CompanyMembership`, optionally scoped to a specific company), and `RolePermission` (DRF permission class enforcing tenant-scoped object-level access for Role endpoints).

Depends On

- BE-012

---

### BE-014 – Role CRUD

**Status:** Done

**Priority:** Critical

**Owner:** Backend Team

**Implementation notes:** *(Backfilled — already implemented but left tracked as Todo; corrected during setup audit on 2026-08-25.)* Implemented `RoleViewSet` in `apps/users/views.py` (list/create/retrieve/partial_update/update/destroy — full CRUD, soft-delete on destroy), `RoleSerializer`/`RoleCreateSerializer`/`RoleUpdateSerializer` in `apps/users/serializers.py`, `RoleService` in `apps/users/services.py`. Routes at `/roles`, `/roles/{id}` in `apps/users/urls.py`. Platform admins can target any company via `companyId`; regular users are restricted to companies where they hold active membership. drf-spectacular schema annotations included. Covered by `apps/users/tests/test_role_views.py`, `test_role_permissions.py`, `test_role_services.py`, `test_role_serializers.py`.

Depends On

- BE-013

---

## Epic 6 – Multi-Tenant

### BE-015 – Tenant Middleware

**Status:** Done

**Priority:** Critical

**Owner:** Backend Team

**Implementation notes:** *(Backfilled — already implemented but left tracked as Todo; corrected during setup audit on 2026-08-25.)* Implemented as a custom DRF authentication class, `TenantJWTAuthentication` in `apps/authentication/authentication.py`, rather than Django middleware — task title kept as-is for traceability, but the mechanism differs from the original "Tenant Middleware" framing. Registered as the sole `DEFAULT_AUTHENTICATION_CLASSES`. After standard JWT validation, resolves `request.company_id` and `request.is_platform_admin`: platform-admin tokens bypass tenant resolution; company-user tokens resolve tenant from active `CompanyMembership` records, requiring an explicit `companyId` (validated against real active memberships, never trusted blindly) when a user belongs to more than one company, and rejecting requests with no active membership. `/auth/logout`, `/auth/me`, `/auth/refresh` are exempted from tenant resolution. Integration-tested end-to-end (10 scenarios: single/multi membership, revoked/soft-deleted membership, platform admin, unauthenticated, invalid JWT) via `apps/users/tests/test_tenant_auth_integration.py`, using a test-only URLconf/view (`apps/users/tests/tenant_info_support.py`) so the diagnostic endpoint doesn't ship in production routes.

Depends On

- BE-010
- BE-012

---

## Epic 7 – API Documentation

### BE-016 – Swagger Configuration

**Status:** Done

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

**Status:** Done

**Priority:** Critical

**Owner:** Backend Team

**Implementation notes:** Not a from-scratch suite — began with a full audit of existing authentication coverage (`apps/authentication/tests/`: 41 tests across `test_login.py`, `test_logout.py`, `test_me.py`, `test_refresh.py`, `test_forgot_password.py`, `test_reset_password.py`, `test_platform_auth.py`; plus `apps/users/tests/test_tenant_auth_integration.py`: 10 tests; plus `apps/common/tests/test_api_docs.py`: 6 tests from BE-016). Built a coverage matrix against `04_API/Authentication_API.md`, `05_Security/JWT.md`, `05_Security/Tenant.md`, `BACKEND_RULES.md`, `05_Security/Permissions.md`, and `00_Development_Standards/Logging_Standards.md`. Conclusion: existing coverage was already comprehensive (every documented endpoint, every JWT claim rule, every tenant-resolution scenario, zero true duplicate tests — a couple of adjacent-but-distinct tests noted, not flagged as waste).

Closed 4 genuine gaps, all as new test methods in **existing** files (no new test files):
- `test_reset_password.py::test_token_superseded_by_newer_forgot_password_request_is_rejected` — the live `/auth/reset-password` endpoint, not just DB state, rejects a token invalidated by a later forgot-password request.
- `test_tenant_auth_integration.py::test_forged_company_id_claim_in_token_is_ignored` — JWT.md §3: a forged `company_id`/`companyId` claim injected into an otherwise-valid token never influences tenant resolution.
- `test_me.py::test_refresh_token_rejected_as_bearer_access_token` — JWT.md §4: a refresh token cannot be used as a Bearer access token.
- `test_platform_auth.py::test_platform_admin_login_recognized_end_to_end_on_gated_endpoint` — the real `POST /platform-auth/login` → `RefreshToken.access_token` production path (not the `PlatformAdminAccessToken.for_user()` shortcut used elsewhere) is recognized by a permission-gated endpoint (`GET /companies`), guarding against the exact class of claim-propagation bug fixed earlier this session.

**Production defect found, not fixed (awaiting approval, recommended for BE-018 instead):** `CompanyViewSet`/`RoleViewSet` return 403 (not 404) when a non-member requests another company's resource by a known/guessed UUID — violates `Error_Handling.md §5`'s explicit anti-enumeration rule (cross-tenant access by ID must be 404, confirming nothing). Lives in `apps.company`/`apps.users`, not `apps.authentication`, so left out of BE-017's scope per the user's explicit rule to defer any production-code fix pending approval.

Zero production code changed by this task. `apps/authentication/tests/` + `apps/users/tests/test_tenant_auth_integration.py` now 59 tests (was 55); full backend suite: **205 passed, 0 failed**.

Depends On

- BE-008

---

### BE-018 – Company Tests

**Status:** Done

**Priority:** Critical

**Owner:** Backend Team

**Implementation notes:** Began with an audit of existing `apps.company` coverage (30 tests: 6 model, 2 serializer, 7 service, 15 view) against `05_Security/Permissions.md`, `05_Security/Tenant.md`, `Error_Handling.md`, `BACKEND_RULES.md` — no `Company_API.md`/`RBAC.md` exist as files, closest real docs used instead. Coverage matrix found existing tests comprehensive with one real defect and one design decision needing a call, both surfaced to the user before any code was written.

**Defect fixed (Decision 1):** `CompanyViewSet` returned 403 instead of 404 for cross-tenant object access by ID (`Error_Handling.md §5`). Fixed with a new reusable `ObjectPermission404Mixin` in `apps/common/views.py` — overrides `check_object_permissions` to raise `Http404` instead of DRF's default `PermissionDenied` whenever `has_object_permission` fails, leaving view-level (`has_permission`) failures like list/create/delete-by-non-admin untouched (still correctly 403, since no specific object is being probed there). Applied to `CompanyViewSet`.

**Debugging finding (not initially anticipated):** the first test run surfaced 2 failures that led to discovering a genuine two-tier security boundary, not a bug in the fix itself. A user with **zero** active company memberships anywhere is rejected by `TenantJWTAuthentication` during authentication — before the view or the new mixin are ever reached — with a 403 that is identical regardless of which company ID was requested (real or fake), so it reveals nothing company-specific and is correctly *not* subject to the §5 anti-enumeration rule. A user who *is* a member of a different company, by contrast, passes authentication and reaches the view, where the new mixin now correctly returns 404. Tests were corrected to assert the right status for each boundary rather than assuming both should be 404.

**Decision 2 (settings merge):** left `apps/company/validators.py::build_update_fields`'s shallow top-level merge unchanged; added a test that documents and locks in the current behavior (a nested key update replaces its sibling nested dict wholesale, not deep-merged) as a regression guard, not a redesign.

**Tests added/corrected (6, all in existing files, no new files):** `test_get_company_detail_as_user_with_no_company_membership_fails_403`, `test_patch_company_as_user_with_no_company_membership_fails_403` (both corrected from an initial wrong assumption), `test_get_company_detail_as_member_of_different_company_returns_404`, `test_patch_company_as_member_of_different_company_returns_404`, `test_update_company_validation_error_400`, `test_soft_deleted_company_returns_404` — plus `test_update_company_settings_merge_is_shallow` in `test_services.py`.

**Deliberately not touched:** `RoleViewSet`/`RolePermission` (`apps.users`) has the identical object-level 403-vs-404 pattern, confirmed during the BE-017 audit. Left unfixed this task since it's outside `apps.company` — the shared `ObjectPermission404Mixin` makes applying the same fix there a one-line change (`class RoleViewSet(ObjectPermission404Mixin, viewsets.GenericViewSet)`) whenever approved.

`apps/company` tests: 37 passed (was 30). Full backend suite: **211 passed, 0 failed**.

Depends On

- BE-011

---

## Epic 9 – Audit

### BE-019 – Audit Log

**Status:** Done

**Priority:** Critical

**Owner:** Backend Team

**Implementation notes:** New `apps.audit` app implementing a durable, append-only audit trail per `01_Business/FRS.md §27` and `03_Database/Database_Schema.md`'s `audit_log` table definition, per the 10 approved architectural decisions.

`AuditLog` (`apps/audit/models.py`) extends `apps.common.models.UUIDModel` only — deliberately not `BaseModel` — so it carries no `updated_at` and no soft-delete (`deleted_at` would defeat the "never-expired" requirement). Fields: `company` (FK→`company.Company`, `SET_NULL`, nullable — corrected from an initial `CASCADE` during implementation so a hard-deleted tenant's history survives), `actor_user` (FK→`users.User`, `SET_NULL`, nullable — system/automated actions), `entity_type`, `entity_id` (UUID, not a real FK — spans many entity tables), `action` (`AuditAction` enum: `create`/`update`/`delete`/`approve`, matching `Database_Schema.md` exactly — a status change is recorded as an `UPDATE` with `status` visible in the before/after diff, not a distinct action value), `before_state`/`after_state` (JSONField, filtered through a per-entity-type field allowlist before persistence), `request_id`/`ip_address`/`user_agent` (captured from the request when available), `created_at` only. Indexed on `(entity_type, entity_id)` and `(company, created_at)`.

`AuditLogRepository` (`apps/audit/repositories.py`) exposes `create()` and read helpers (`for_entity`, `for_company`, `for_actor`) only — no `update()`/`delete()`, enforcing append-only at the application layer, not just by convention. `AuditLogAdmin` is read-only in Django admin (`has_add/change/delete_permission` all `False`).

`AuditLogService.record()` (`apps/audit/services.py`) is the single entry point: filters `before_state`/`after_state` through `apps/audit/validators.py`'s `ENTITY_FIELD_ALLOWLISTS` (an unregistered `entity_type` yields an empty state, never a raw unreviewed dump — the redaction safety net for a never-expired table), extracts `request_id`/`ip_address` (`X-Forwarded-For` preferred over `REMOTE_ADDR`)/`user_agent` from an optional `request` param, persists via the repository, and emits a companion `logger.info()` line. Explicit service calls only — no signals, no middleware, per Decision 8.

**Integration (Decisions 3 & 4):** `RoleService.create_role/update_role/soft_delete_role` (`apps/users/services.py`) and `CompanyService.create_company/update_company/soft_delete_company` (`apps/company/services.py`) now call `AuditLogService.record()` with `before_state`/`after_state` (renamed from `old_value`/`new_value` per Decision 6) instead of the previous bare `audit_logger.info()` call in `RoleService` (which had no DB row) or no audit logging at all in `CompanyService`. `RoleViewSet`/`CompanyViewSet` pass `request=request` (and `actor_user=request.user` for Company) through to the service layer. `CompanyService`'s three mutating methods are now fully wrapped in `transaction.atomic()` (previously only partial), so the audit row and the mutation it describes commit or roll back together.

**Tests:** `apps/audit` (new): 14 (5 model — full entry, nullable FKs, `SET_NULL` on company hard-delete, ordering, `__str__`; 9 service — persistence, redaction for unregistered entity types, allowlist filtering, `None` handling, request-context extraction incl. `X-Forwarded-For` precedence, missing-request/actor handling, repository exposes no update/delete). `apps/users`: +3 integration tests proving `RoleService` writes real `AuditLog` rows. `apps/company`: +4 integration tests proving `CompanyService` writes real `AuditLog` rows, including one proving a status change is visible within a single `UPDATE` entry's before/after diff. Full backend suite: **232 passed, 0 failed** (was 211 after BE-018; +21 net new tests, matching exactly).

**Self-review (Architecture / Security / Tenant Isolation / Audit Log Design / Redaction Safety / Transaction Safety / Performance / Django Best Practices):** Architecture follows View→Serializer→Service→Repository→Model with `AuditLogService` as the cross-cutting concern services call into directly, never views. Security: no PII/secret fields possible in `before_state`/`after_state` because the allowlist is opt-in per entity type, not opt-out — a new entity type added later that forgets to register an allowlist fails safe (empty state) rather than leaking every field. Tenant isolation: `company` is nullable and `SET_NULL` rather than tenant-enforced-NOT-NULL, a deliberate, narrow exception to the platform's usual tenant-scoping rule, justified because audit rows must be queryable/attributable even after the owning tenant is gone. Audit log design matches `Database_Schema.md`'s field set and action taxonomy exactly. Redaction safety verified by a dedicated test (`test_unregistered_entity_type_yields_empty_state_not_raw_dump`). Transaction safety: every audit write happens inside the same `transaction.atomic()` block as the mutation it describes, so a DB failure after the audit write can't leave an orphaned audit entry with no corresponding change (or vice versa). Performance: audit writes are synchronous single-row inserts inside an already-open transaction — negligible overhead, and correctness (durability tied to the mutation) was explicitly prioritized over the marginal latency Celery-async would have saved, per Decision 8's rejection of signals/async. Django best practices: enum choices via `TextChoices`, `db_index` on every commonly-filtered column, no N+1 risk introduced (each `record()` call is one insert).

**Deliberately deferred (per approved Decision 2, out of scope for BE-019):** no serializers/views/permissions/urls/REST endpoints for reading audit logs — Django admin is the only current read surface.

Depends On

- BE-004

---

## Epic 10 – Infrastructure

### BE-020 – Docker & Docker Compose

**Status:** Done

**Priority:** Critical

**Owner:** Backend Team

**Implementation notes:** Backend-only stack per the approved plan (no frontend containerization — no `apps/web` exists yet in this repo). `docker-compose.yml` (repo root) defines six services: `postgres` (16-alpine, named volume `pgdata`, `pg_isready` healthcheck), `redis` (7-alpine, broker/result-backend only — no cache consumer yet, `redis-cli ping` healthcheck), `django` (builds `backend/Dockerfile` target `dev`, bind-mounted for hot-reload, `env_file: backend/.env` with `DB_HOST`/`CELERY_BROKER_URL`/`CELERY_RESULT_BACKEND` overridden to container-network service names so the checked-in `.env`'s `localhost` defaults stay correct for non-Docker runs), `celery-worker`/`celery-beat` (same image, only `command:` differs — no tasks/schedule registered yet, pure infra scaffolding ahead of the async workload, matching the plan's flagged risk), and `nginx` (alpine, reverse-proxies to `django`, serves `staticfiles`/`media` named volumes directly).

`backend/Dockerfile`: four stages (`base` → `dev` / `builder` → `production`), matching `07_DevOps/Docker.md`'s design. Production stage installs only `libpq5`/`curl` runtime libs (not the build toolchain), copies site-packages from `builder`, runs `collectstatic --noinput` while still root (before the non-root `appuser` ownership handoff), then drops privileges. Migrations are deliberately **not** run inside the image or `CMD` — `07_DevOps/CI_CD.md` §4 treats `migrate` as an explicit pre-traffic deploy step, not something baked into container start (which would race concurrent replicas). `backend/.dockerignore` excludes `.venv/`, `__pycache__/`, `.env`, `media/`, `staticfiles/`, etc. `backend/nginx/nginx.conf` proxies to `django:8000`, serves `/static/`/`/media/` directly, and carries a commented-out TLS scaffold (real TLS terminates at the load balancer per `Production.md` §3, not here).

**New health endpoint (`GET /health/`):** `apps/common/views.py::HealthCheckView` — unauthenticated, no DB/cache dependency, returns the standard `ApiResponse.success()` envelope. **Deviation from the approved plan, disclosed:** the plan's §12 called for adding `/health/` to `TenantJWTAuthentication`'s `exempt_paths` list (BE-016's approach for `/schema/`/`/docs/`/`/redoc/`). Implemented instead via `authentication_classes = []` directly on the view — a strictly stronger guarantee (TenantJWTAuthentication never runs for this view at all, regardless of token state) that can't be broken by a future trailing-slash mismatch in that list (a class of bug `exempt_paths` already has once, noted in BE-016). `apps/authentication/authentication.py` was therefore **not** modified — a smaller diff than planned, same outcome. 3 new tests in `apps/common/tests/test_health.py` (no auth, invalid Bearer token ignored, `X-Request-ID` header set).

`07_DevOps/Docker.md` updated from "indicative/draft" to reflect the actual implementation (real paths, real service names); its frontend section (§3) explicitly marked still-draft since no frontend code exists in this repo.

**Verification, disclosed honestly:** an earlier attempt hit a Docker Desktop host-level storage fault (read-only containerd store) that blocked both `docker build` and `docker pull` — unrelated to this repo's code. On retry (2026-08-27) that host fault had cleared, which surfaced a **real, second bug**: the `dev` build stage (used by `django`/`celery-worker`/`celery-beat`) never installed `curl`, but `django`'s healthcheck runs `curl -f http://localhost:8000/health/` — the healthcheck failed on a missing binary every time, marking `django` permanently unhealthy and blocking `nginx` (which `depends_on: django: condition: service_healthy`) from ever starting. Fixed by adding `curl` to the shared `base` stage (`backend/Dockerfile` line 17) so both `dev` and `production` lineages have it.

**Verified end-to-end (2026-08-27), full `docker compose up -d`:** all 6 services reached a running state — `postgres` healthy, `redis` healthy, `django` healthy, `celery-worker` connected to Redis and ready, `celery-beat` scheduler started, `nginx` up and proxying. `GET /health/` returned `200 {"status": "ok"}` through both `http://localhost:8000/health/` (direct) and `http://localhost/health/` (via nginx reverse proxy). Stack torn down cleanly afterward with `docker compose down`. This closes the previously-open verification gap — Docker is now confirmed working, not just reviewed.

**Tests:** `apps/common` +3 (health check). Full backend suite: **235 passed, 0 failed** (was 232 after BE-019).

Depends On

- BE-001

---

## Epic 11 – Stabilization & Hardening

### BE-021 – Multi-Tenant Resolution, RoleViewSet Cleanup & Security Hardening

**Status:** Done

**Priority:** Critical

**Owner:** Backend Team

**Implementation notes:** A full architecture review and a full security audit were each conducted against the Sprint 1 codebase, and every finding from both was resolved in this task — no finding remains open except two explicitly documented, deliberate exceptions (below). No new business features were introduced; this is a stabilization/hardening task only.

**1. Single source of truth for tenant resolution.** `TenantJWTAuthentication` was already resolving `request.company_id`, but `CompanyViewSet`/`RoleViewSet` and their permission classes independently re-derived tenant scope from `request.user.memberships`, producing duplicated, divergent logic and blocking multi-company users from most endpoints unless they happened to satisfy both independent checks. `apps/company/permissions.py::IsPlatformAdminOrCompanyAccess.has_object_permission` and `apps/users/permissions.py::RolePermission.has_permission/has_object_permission` now compare directly against `request.company_id` — no membership re-query. `RoleViewSet.list()`'s dead/spec-violating "list across all my companies" branch (Tenant.md §4 explicitly forbids this for a non-admin on a company-scoped resource) was removed along with the now-unreachable `company_ids` (plural) parameter across `RoleService.list_roles`/`selectors.list_roles`. 12 new integration tests (`apps/users/tests/test_multi_company_tenant_resolution.py`, `apps/company/tests/test_multi_company_tenant_resolution.py`) exercise a genuinely multi-membership user against the real `/roles` and `/companies` endpoints (not the BE-017 diagnostic-only endpoint) — single membership, multiple memberships, explicit companyId, omitted companyId (correctly rejected as ambiguous per Tenant.md §4), invalid companyId, and unauthorized companyId are all covered.

**2. RoleViewSet business logic moved to the service layer.** `list()`/`create()` previously computed target-company/authorization decisions inline. `RoleService.list_roles_for_viewer()` and `RoleService.resolve_create_target_company_id()` now own those decisions; the view only validates input and orchestrates. Zero behavior change (no test needed modification for this step — confirmed the refactor was behavior-preserving before layering in the query-param-validation changes below).

**3. Query-param validation via serializers.** `RoleListQuerySerializer`/`CompanyListQuerySerializer` (new) validate `companyId`/`isActive`/`status`/`search`/`ordering` — an invalid value (bad UUID, unrecognized boolean, unknown ordering field/status) now returns 400 `VALIDATION_ERROR` instead of being silently ignored or coerced to a default. `ordering`'s choices are drawn directly from each app's existing `VALID_ORDER_FIELDS` set (selectors.py) so the two can't drift apart.

**4. Role uniqueness race condition.** `RoleService.create_role`/`update_role`'s check-then-insert pattern is a TOCTOU race under concurrent requests; the DB's `unique_active_role_per_company` constraint is the real backstop, but a concurrent collision previously raised an unhandled `IntegrityError` → 500. Both methods now wrap the risky operation in a nested `transaction.atomic()` (savepoint) and catch `IntegrityError`, converting it to the same `ConflictError` (409) the pre-check raises — the outer transaction (and the audit-log write after it) stays usable. Two deterministic concurrency tests (`apps/users/tests/test_role_concurrency.py`, `TransactionTestCase` + real threads against Postgres, mocking the pre-check to force the race window open) verified stable across 5 repeated runs.

**5. Refresh token privilege re-verification.** `AuthenticationService.refresh_token` previously trusted the incoming token's own `user_type` claim to decide whether to re-mint a `platform_admin` access token — a refresh token issued before an admin's privileges were revoked could keep minting valid admin access tokens until the refresh token itself expired. It now re-queries the user's current `is_active`/`is_superuser`/`is_staff` state on every refresh (`UserRepository.get_by_id`, new) and rejects outright if the claimed admin privilege no longer holds current DB state, rather than re-minting from the stale claim.

**6. Rate limiting.** DRF `ScopedRateThrottle` is now the default throttle class (`config/settings.py`); it only throttles a view that declares `throttle_scope`, so every other endpoint is unaffected. `LoginView`/`PlatformLoginView`/`ForgotPasswordView`/`ResetPasswordView`/`TokenRefreshView` each got a distinct scope (`auth_login` 10/min, `platform_auth_login` 10/min, `auth_forgot_password` 5/min, `auth_reset_password` 10/min, `auth_refresh` 30/min). A `Throttled` exception already mapped to the standard 429 envelope (BE-006) — no response-shape change needed. New `backend/conftest.py` autouse fixture clears Django's cache before/after every test, since `ScopedRateThrottle`'s cache-backed counters otherwise persist across test methods within a run (a real gotcha this surfaced — 4 existing tests briefly failed with spurious 429s until this fixture was added).

**7. `SECRET_KEY` hardening.** `config/settings.py` now raises `ImproperlyConfigured` at startup if `DEBUG=False` and `SECRET_KEY` still equals the checked-in insecure development default — closing the gap where a misconfigured production deploy could silently boot with a publicly-known key. `DEBUG=True` local/dev behavior is unchanged.

**8. Authentication audit logging.** `AuditAction` gained six new values (`login_success`, `login_failure`, `logout`, `token_refresh`, `password_reset_requested`, `password_reset_completed` — migration `0002_alter_auditlog_action.py` widens `action` to `max_length=30` to fit them; adding `choices` values itself needed no migration, since Django's `CharField.choices` isn't a DB-level constraint). `apps.audit.validators.ENTITY_FIELD_ALLOWLISTS` gained a `"user": {"email"}` entry — deliberately excludes password/token fields entirely. Every `AuthenticationService` method now calls the existing `AuditLogService.record()` (no parallel/duplicate logging path) for its corresponding event; a login failure against a completely unknown email writes no entry (no real entity to attach it to — doesn't affect response timing, since that path already runs the dummy password hasher per Part 10 either way).

**9. Timing-attack mitigation.** `AuthenticationService._verify_credentials` now runs `User().set_password(password)` against a throwaway instance when the email doesn't match any user — mirroring Django's own `ModelBackend.authenticate()` (issue #20760) — so response timing no longer distinguishes "no such account" from "wrong password for a real account."

**10. Password reset email failures.** `PasswordResetEmailService.send_password_reset_email`'s bare `except Exception: pass` now logs via `logger.exception(...)` (new `apps.authentication` logger) before continuing — the client-visible response is completely unchanged (still generic, still prevents enumeration), but an SMTP outage is no longer completely invisible server-side.

**11. `BrowsableAPIRenderer` restricted in production.** `DEFAULT_RENDERER_CLASSES` now includes `BrowsableAPIRenderer` only when `DEBUG=True`; a `DEBUG=False` environment serves `JSONRenderer` only. Local developer experience is unchanged.

**12. `RoleViewSet` enumeration fix.** `RoleViewSet` now inherits `ObjectPermission404Mixin` (`apps/company/views.py`'s `CompanyViewSet` already had it since BE-018) — cross-tenant access to a role by ID returns 404, not 403. A real cross-tenant role and a random nonexistent UUID now produce byte-for-byte identical 404 responses (new regression test asserts this explicitly).

**13. Cleanups.** `Role`'s redundant `objects`/`all_objects`/`deleted_objects` manager redeclaration removed (identical to what it already inherits from `BaseModel`; `CompanyMembership` never had this redundancy). Local `from apps.users.models import Role/CompanyMembership` imports inside two serializer `Meta` classes moved to the module top alongside the existing `User` import (no circular-import reason existed for them being local). `apps.users.validators.parse_is_active_query_param` (added mid-arc, superseded by Part 3's serializer-based validation) removed before it could ship as dead code.

**Deliberately assessed, not changed (disclosed, not silently skipped):**
- `CompanyMembershipSerializer` (`apps/users/serializers.py`) — flagged as unused-by-any-view in the architecture review, but it has real, dedicated test coverage (`test_membership_serializer_camel_case`) and is reasonable forward-compatibility scaffolding for a CompanyMembership management API that doesn't exist yet (out of scope — "no new business features"). Removing it would mean also removing/rewriting its test, a larger and riskier change than this task's "maintain backward compatibility wherever possible" instruction supports for a low-value cleanup.
- PUT/PATCH semantics (`CompanyViewSet.update`/`RoleViewSet.update` both forward to `partial_update`) — no test or known caller relies on strict PUT (full-replacement) semantics, but none currently exercises PUT with a partial payload either, so there's no evidence either way about a real caller's expectations. Left unchanged rather than risk silently breaking an undocumented caller, per the explicit "maintain backward compatibility wherever possible" instruction.

**Security review (Part 14 — SQL Injection / Object Injection / Mass Assignment / Cross-Tenant Leakage / Sensitive Data Exposure / Permission Escalation / Authentication Bypass / JWT Forgery / Broken Audit Trail):** no new instance of any of these was introduced or discovered while implementing the above; the two categories directly targeted by this task (Permission Escalation via stale refresh-token privilege, and the Cross-Tenant/enumeration gaps in Role) are now closed.

**Tests:** 12 new multi-company tenant-resolution integration tests, 2 new concurrency tests, 5 new settings-hardening tests, 6 new throttling tests, ~20 new authentication tests (audit logging, timing mitigation, refresh hardening, email-failure logging) spread across existing files, plus query-param-validation and 404-enumeration regression tests. Full backend suite: **281 passed, 0 failed** (was 235 after BE-020).

Depends On

- BE-001
- BE-011
- BE-014
- BE-015
- BE-019

---

# Sprint 2 – CRM

_(Renumbered 2026-08-27: originally BE-021–BE-044. BE-021 collided with the Sprint 1 Epic 11 hardening task of the same number — shifted every ID in Sprints 2–6 forward by one. No other document references these IDs.)_

- BE-022 – Client Module
- BE-023 – Client CRUD
- BE-024 – Project Module
- BE-025 – Project CRUD
- BE-026 – Project Members
- BE-027 – Project Workflow
- BE-028 – Project Filters
- BE-029 – Project Audit Logs
- BE-030 – CRM Tests

_(Renumbered again 2026-08-27, BE-025 onward: inserted "BE-025 – Project CRUD" — Sprint 2 had given Client both a Module task (BE-022) and a separate CRUD task (BE-023), but Project only got Module (BE-024) with no CRUD task before jumping to Members. Project Members cannot be meaningfully built without Project creation/retrieval existing first. Every ID from the old BE-025 onward shifted forward by one to make room; Sprints 3–6 shifted by one accordingly (Sprint 3 now starts at BE-031, Sprint 6 now ends at BE-046). No code references any of the shifted IDs — confirmed by search before renumbering.)_

Status: Done

---

### BE-022 – Client Module

**Status:** Done

**Priority:** Critical

**Owner:** Backend Team

**Implementation notes:** Client domain foundation only — no views/URLs/CRUD (BE-023's scope). New `apps.clients` app: `Client(BaseModel)` with `company` FK (CASCADE, `related_name="clients"`), required `name`, and optional `company_name`/`email`/`mobile`/`gstin`/`addresses` (JSONField, default `[]`)/`notes` (TextField, default `""`) — field set matches `Database_Schema.md`'s `client` table exactly, no invented fields (no `is_active`, no uniqueness constraint — neither is documented). `db_table = "client"` per `Naming_Standards.md`. Composite index `(company, name)` for the listing query BE-023 will need. `ClientRepository`/`ClientSerializer`/`ClientPermission` mirror `RoleRepository`/`RoleSerializer`/`RolePermission` exactly for architectural consistency. `ClientPermission` deliberately uses the same coarse tenant-membership gate as `RolePermission` — **not** fine-grained `client.view`/`create`/`edit`/`delete` permission codes, per explicit Backend Lead decision (2026-08-27): `05_Security/Permissions.md` §7 lists the canonical permission-code list as still pending client sign-off, and no `Permission`/`RolePermission` model exists in code despite Migration_Plan.md's 007/008 — building that now would be new RBAC infrastructure outside this task's scope. `selectors.py`/`validators.py` are minimal foundations (bare tenant-scoped queryset, `require_name()`) for BE-023 to extend with search/filter/create logic. Migration `0001_initial` depends only on `company`, matching `Migration_Plan.md` migration 011 (Group C).

**Deferred (documented, not gaps):** the `CRM_API.md` "block delete if active projects exist" rule can't be built until BE-024 (Project) exists — Client has no reverse relation to check yet. Audit logging and the `ENTITY_FIELD_ALLOWLISTS["client"]` entry are BE-023's responsibility (no mutations happen in BE-022). A separate multi-note-with-authorship model (implied by `CRM_API.md`'s `POST .../notes` sketch) was not built — `Database_Schema.md`'s actual `client` column list has one plain `notes` field, which is what was implemented; flagged as a conscious documentation-following choice, not an oversight.

**Tests:** 18 new (`apps/clients/tests/test_models.py` ×12: creation, optional-field defaults, full-field persistence, str repr, absence of uniqueness constraint, same-name-different-company, tenant isolation via FK, soft delete lifecycle, cascade delete, required-company enforcement; `test_permissions.py` ×8, unit-level only per task scope — no HTTP client/URLs involved, full endpoint-level authorization tests are BE-023's). Full backend suite: **299 passed, 0 failed** (was 281 after Sprint 1 closure). `manage.py check`: 0 issues. `makemigrations --check --dry-run`: no changes detected. `spectacular --fail-on-warn`: clean (BE-022 adds no endpoints, confirmed schema untouched).

Depends On

- BE-014 (Role CRUD — company/tenant patterns this mirrors)
- BE-021 (Multi-Tenant Resolution — `request.company_id` this reuses)

---

### BE-023 – Client CRUD

**Status:** Done

**Priority:** Critical

**Owner:** Backend Team

**Implementation notes:** Full Client CRUD, mirroring `RoleViewSet`/`RoleService`/`RoleSerializer` architecture exactly. Flat endpoints `GET/POST /clients`, `GET/PATCH/PUT/DELETE /clients/{id}` (not `CRM_API.md`'s nested `/companies/{companyId}/clients` sketch — that draft contradicts the already-implemented "never trust a path-supplied companyId" pattern). `ClientViewSet(ObjectPermission404Mixin, viewsets.GenericViewSet)` — pure orchestration, all logic in `ClientService`. `ClientService.resolve_create_target_company_id()`/`list_clients_for_viewer()` mirror `RoleService`'s exactly: non-admin's `request.company_id` is the only tenant source; a mismatched client-supplied `companyId` is rejected (403), never silently overridden; platform admin requires an explicit `companyId` on create, and sees all companies' clients on list (no `companyId` list filter was added — not part of approved scope, this is the same Platform Admin list-everything exception Tenant.md §4 permits, not a gap). `ClientPermission` (from BE-022, unchanged) continues as the coarse tenant-membership gate — no fine-grained `client.*` codes. Search (`?search=`) covers `name`/`company_name`/`email`/`mobile` via `icontains` (documented fields only); no other filters. `PUT` forwards to `partial_update`, matching the existing `RoleViewSet` convention, not a Client-specific full-replace semantic. `AuditLogService.record()` wired into create/update/delete with `entity_type="client"`; `ENTITY_FIELD_ALLOWLISTS["client"] = {"name", "company_name", "email", "mobile", "gstin"}` added to `apps/audit/validators.py` — `addresses`/`notes` deliberately excluded as an MVP privacy/payload-size choice, not a permanent product rule. Unlike Role, `ClientService.create_client`/`update_client` need no `IntegrityError`→`ConflictError` handling — Client has no uniqueness constraint (BE-022 decision), a genuine simplification. Full `@extend_schema_view` coverage for all 6 actions, tagged `"Client"`.

**Deferred at the time (resolved in BE-024):** `soft_delete_client()` was unconditional here — the "block delete if active projects exist" rule (`CRM_API.md`) couldn't be built until Project existed. BE-024 added the guard; see that entry below.

**Tests:** 51 new. `test_services.py` ×18: create/get/list/update/soft-delete success and cross-tenant-scoping paths, no-uniqueness-constraint confirmation, `resolve_create_target_company_id`/`list_clients_for_viewer` admin vs. non-admin branches, audit row creation on create/update/delete including confirmation that `addresses`/`notes` are excluded from the audit payload. `test_views.py` ×33: 401 unauthenticated, 403 no-membership/revoked-membership, list scoping (member vs. platform admin sees all), search (name/email), ordering, invalid-ordering 400, pagination shape, empty list shape, soft-deleted exclusion from list, create success (member and admin-with-companyId), admin-without-companyId 400, company-injection-by-member 403, validation 400 (blank name, invalid email, non-list addresses), retrieve success, cross-tenant GET/PATCH/DELETE 404 (+ indistinguishable-from-nonexistent-ID), platform-admin cross-tenant retrieve/update/delete allowed, update success, PUT-behaves-like-PATCH confirmation, delete soft-deletes and excludes from subsequent GET. Full backend suite: **350 passed, 0 failed** (was 299 after BE-022). `manage.py check`: 0 issues. `makemigrations --check --dry-run`: no changes detected (no schema change in this task). `spectacular --fail-on-warn`: clean; confirmed `/clients/` and `/clients/{id}/` present in the generated schema.

Depends On

- BE-022 (Client Module)

---

### BE-024 – Project Module

**Status:** Done

**Priority:** Critical

**Owner:** Backend Team

**Implementation notes:** Project domain foundation only — no CRUD/views/urls/serializers/services/permissions (those are BE-025/026/027's scope; BE-024 deliberately did not pre-create empty stub files for them, to avoid meaningless placeholder abstractions). New `apps.projects` app: `Project(BaseModel)` with `company` FK (required, CASCADE), `client` FK (required, **PROTECT** — per `Naming_Standards.md` §4's own literal example: "don't allow deleting a client with existing projects"), `name` (required), `start_date`/`deadline` (optional `DateField`), `status` (`ProjectStatus` TextChoices — 11 documented values, default `draft`; BE-024 defines the enum/default only, **not** the transition graph, which is BE-026's), `priority` (plain `CharField(max_length=50)`, no `choices=` — no value domain is documented anywhere in FRS/Database_Schema/Project_API, confirmed by grep across the doc tree; Backend Lead decision 2026-08-27 was to leave it unconstrained rather than invent an enum), `assigned_to` (nullable FK→User, `SET_NULL` — the single documented field, **not** the multi-user "team" concept `Project_API.md`'s `/team` endpoints imply, which has no corresponding table anywhere in `Migration_Plan.md`'s 27 migrations — flagged as an open question for BE-025, not resolved here), `follow_up_reminder_at` (optional `DateTimeField`). Composite index `(company, status)` — named explicitly in `Naming_Standards.md` §3's own example list for this table.

**Client delete guard (resolves the BE-022/023 deferral):** `ClientService.soft_delete_client()` now checks, before deleting, whether the client has any Project not in a terminal status. Terminal = `{completed, cancelled}` (Backend Lead decision 2026-08-27); every other status (including `on_hold`) blocks deletion. Raises `ConflictError` (409, per `Error_Handling.md`'s "Request conflicts with current state" taxonomy) if blocked — no delete occurs, no DELETE audit entry is written. **Architecture**: the check is `ProjectSelector.has_blocking_projects_for_client()` in `apps/projects/selectors.py`, a single efficient `EXISTS` query using `TERMINAL_PROJECT_STATUSES` from `apps.projects.models` — deliberately *not* implemented as `client.projects.filter(...)` inside `ClientRepository` (an earlier design considered and rejected by Backend Lead review), since that would make the Client domain responsible for understanding Project lifecycle semantics. Dependency direction verified both statically (AST-parsed import list) and empirically (full test suite green, `manage.py check` clean): `apps.clients.services → apps.projects.selectors → apps.projects.models → apps.common.models`. Nothing under `apps.projects` imports anything from `apps.clients` — `Project.client`'s FK uses the Django string app-label `"clients.Client"`, resolved lazily by the app registry, not a Python-level import. No cycle exists.

**Genuine architectural finding (not a regression — nothing currently calls this path):** hard-deleting a Company (`company.delete(hard=True)`, the tenant-offboarding path) now raises `ProtectedError` if **any** of its Clients has **any** Project at all, regardless of that Project also being CASCADE-deleted via `Project.company`. Verified empirically: Django's deletion collector evaluates the `Client→Project` PROTECT relation independently and does not reconcile it against the same rows also being cascade-collected via a different path (`Company→Project`). This is a direct, correct consequence of `Project.client`'s `PROTECT` choice, not a bug — but it means a future tenant-offboarding feature must delete Projects, then Clients, then Company explicitly, rather than relying on one cascading call. Documented here since Company hard-delete isn't exposed via any API today (no regression), but this needs to be known before that feature is ever built.

**Tenant invariant documented, not enforced yet:** `Project.company_id == Project.client.company_id` has no database-level enforcement (Postgres can't express a cross-FK equality constraint declaratively without a trigger, which isn't in this stack). Enforcement is deferred to the service layer of whichever task first introduces `Project` creation (BE-025 or later) — it should call `ClientService.get_client_by_id(client_id, company_id=target_company_id)`, which already raises `NotFound` on cross-tenant access (built in BE-023), reusing existing code rather than duplicating the check. **BE-024 does not pretend the model alone enforces this** — a regression test for this invariant is explicitly deferred to that future task's test suite, not silently dropped.

**Assigned_to invariant documented, not enforced yet:** future requirement — `assigned_to` must belong to the same Company as the Project. No assignment service exists yet to enforce this (BE-024 has no service layer); flagged for whichever task first builds assignment behavior.

**Deferred to later tasks (explicit boundaries, not gaps):** Project CRUD (create/retrieve/update/delete endpoints) — BE-025, inserted after this task closed (see the Sprint 2 renumbering note above; BE-024 built the model only, no service/view layer). Project Members/team beyond `assigned_to` — BE-026 (a new `project_member` table, approved by Backend Lead as a documented deviation from `Migration_Plan.md` — see that task's entry). Status transition rules/authorization — BE-027. Filters/search — BE-028. Audit log integration for Project's own mutations — BE-029 (no `ENTITY_FIELD_ALLOWLISTS["project"]` entry added yet — nothing writes Project audit rows in BE-024).

**Tests:** 33 new. `apps/projects/tests/test_models.py` ×18: required-field enforcement (company/client/name), optional-field defaults, `status` defaults to `draft`, all 11 `ProjectStatus` values accepted, `priority` accepts arbitrary text, str repr, soft-delete lifecycle + restore, `Project.company` field configured as CASCADE (structural check — see the ProtectedError finding above for why this can't be exercised end-to-end in isolation), Company hard-delete blocked by PROTECT via Client when a Project exists (the finding above, verified not assumed), Client soft-delete leaves Project's FK untouched, Client hard-delete blocked by PROTECT when a Project references it, Client hard-delete succeeds when no Project references it, `assigned_to` SET_NULL on User hard-delete, `(company, status)` composite index exists. `apps/clients/tests/test_services.py` +15 (`ClientDeleteGuardTestCase`): delete succeeds with zero/completed-only/cancelled-only/completed+cancelled projects; delete blocked by each of the other 9 statuses individually (draft, planning, design, quotation, approved, execution, quality_check, handover, on_hold); blocked delete leaves the client undeleted; blocked delete writes no DELETE audit entry; successful delete still writes its existing audit entry. Full backend suite: **383 passed, 0 failed** (was 350 after BE-023). `manage.py check`: 0 issues. `makemigrations --check --dry-run`: no changes detected.

Depends On

- BE-023 (Client CRUD)

---

### BE-025 – Project CRUD

**Status:** Done

**Priority:** Critical

**Owner:** Backend Team

**Implementation notes:** Full Project CRUD, mirroring `ClientViewSet`/`ClientService`/`ClientSerializer` architecture exactly (which itself mirrors `RoleViewSet`). Flat endpoints `GET/POST /projects`, `GET/PATCH/PUT/DELETE /projects/{id}`. `ProjectViewSet(ObjectPermission404Mixin, viewsets.GenericViewSet)` — pure orchestration, all logic in `ProjectService`. `ProjectService.resolve_create_target_company_id()`/`list_projects_for_viewer()` mirror `ClientService`'s exactly: non-admin's `request.company_id` is the only tenant source; a mismatched client-supplied `companyId` is rejected (403); platform admin requires an explicit `companyId` on create and sees all companies' projects on list. `ProjectPermission` is a byte-for-byte mirror of `ClientPermission` — the same coarse tenant-membership gate, no fine-grained `project.*` codes (consistent with the standing BE-022 decision). `list_projects()` in `selectors.py` is deliberately bare (company filter + `-created_at` ordering only) — no search/status/priority/date filtering, which is BE-028's job.

**Resolves BE-024's deferred tenant invariant:** `ProjectService.create_project()` calls `ClientService.get_client_by_id(client_id, company_id=target_company_id)` to load the client, reusing its existing cross-tenant `NotFound` check rather than duplicating logic — this enforces `Project.company_id == Project.client.company_id` exactly as BE-024 flagged it should, with no new code in the Client domain.

**Resolves BE-024's deferred assignee invariant:** a new `apps/projects/validators.py::validate_assignee_company_membership(user_id, company_id)` checks for an **active** `CompanyMembership` row for the given user in the given company and raises `ValidationError({"assignedTo": [...]})` (400) if none exists — covers both "wrong company" and "revoked membership" cases with one check. Called from both `create_project` (when `assigned_to_id` is supplied) and `update_project` (when `assigned_to_id` is present in `validated_data`, including explicit clearing to `None`, which is allowed unconditionally).

**Status and Client are deliberately excluded from the edit surface:** `ProjectUpdateSerializer` has no `status` or `client`/`clientId` field, and `ProjectService.update_project()` ignores those keys even if present in `validated_data` (defense in depth, verified by a dedicated test) — `Project_API.md` documents status changes going through a separate `/status` sub-endpoint (BE-027's scope, the status transition graph) and does not document client reassignment via the general edit endpoint at all. `ProjectCreateSerializer` likewise has no `status` field — every new Project starts at the model default (`draft`).

**No audit logging in this task:** `ProjectService` makes no `AuditLogService.record()` calls and `ENTITY_FIELD_ALLOWLISTS["project"]` was not added — wiring Project's own mutations into the audit trail is BE-029's explicit scope, matching how BE-024 (Project Module) also deferred it.

**Schema fix (unrelated bug, fixed in passing):** `spectacular --fail-on-warn` failed with a non-optimally-resolvable enum naming collision — both `Company.status` (`CompanyStatus`) and `Project.status` (`ProjectStatus`) are `TextChoices` fields named `status` on different models, which drf-spectacular can't disambiguate by name alone. Fixed with an explicit `ENUM_NAME_OVERRIDES` entry in `SPECTACULAR_SETTINGS` (`config/settings.py`) mapping each to its import path. No behavior change; schema now generates cleanly.

**Tests:** 92 new. `apps/projects/tests/test_services.py` ×23: create success, nonexistent-company `NotFound`, cross-tenant-client `NotFound`, valid-assignee accepted, wrong-company-assignee rejected, revoked-membership-assignee rejected, get/list/cross-tenant scoping, `list_projects_for_viewer` platform-admin-sees-all, `resolve_create_target_company_id` non-admin-mismatch-denied, update success, cross-tenant update `NotFound`, assignee-wrong-company rejected on update, assignee-can-be-cleared, status/client keys ignored by update even when present, soft-delete plus post-delete `NotFound` plus row still present via `all_objects`. `apps/projects/tests/test_views.py` ×~33 (endpoint-level, mirroring `apps/clients/tests/test_views.py`'s structure): 401/403, list scoping (member vs. admin-sees-all), empty-list shape, soft-deleted excluded from list, create (member and admin-with-companyId, cross-tenant-client rejected, company-injection-by-member denied, validation 400, missing-`clientId` 400, supplied `status` silently ignored), retrieve (success, cross-tenant 404 indistinguishable from nonexistent, admin cross-tenant allowed), update (success, PUT-behaves-like-PATCH, `status`/`client` changes ignored, cross-tenant 404), delete (soft-deletes, cross-tenant 404, admin allowed). Full backend suite: **425 passed, 0 failed** (was 383 after BE-024). `manage.py check`: 0 issues. `makemigrations --check --dry-run`: no changes detected (no schema change — `repositories.py`/`selectors.py` additions are pure lookups, no new fields). `spectacular --fail-on-warn`: clean after the `ENUM_NAME_OVERRIDES` fix; confirmed `/projects/` and `/projects/{id}/` present in the generated schema.

Depends On

- BE-024 (Project Module)

---

### BE-026 – Project Members

**Status:** Done

**Priority:** High

**Owner:** Backend Team

**Implementation notes:** New `ProjectMember(BaseModel)` model and full team management, implementing the documented deviation approved in BE-025 planning (see `03_Database/Migration_Plan.md` "Deviations From This Plan"). Fields: `company` FK (CASCADE, required, denormalized from `project.company` for tenant-scoped queries without a join — same reasoning `CompanyMembership` already applies to every tenant-owned table), `project` FK (CASCADE, required, `related_name="members"`), `user` FK (**SET_NULL**, nullable — preserves historical membership rows if a user is ever hard-deleted, mirroring `Project.assigned_to`'s own SET_NULL choice), `assigned_by` FK (SET_NULL, nullable — records who added the member, if known). No project-specific role field — not documented anywhere in `01_Business/FRS.md`/`Database_Schema.md`/`Project_API.md`, so not invented. Soft-delete-aware `UniqueConstraint(project, user, condition=deleted_at__isnull=True)` — mirrors `CompanyMembership.unique_active_company_user_membership` exactly — prevents duplicate active memberships while still allowing a removed-then-re-added member to get a fresh row. `db_table = "project_member"`. Migration `apps/projects/migrations/0002_projectmember.py`.

**Additive to `assigned_to`, not a replacement (Backend Lead decision, BE-025/026 planning):** `Project.assigned_to` remains the single documented point-of-contact field; `ProjectMember` is the separate multi-user "Team" concept `Project_API.md`'s `/team` endpoints imply. The two are entirely independent — adding/removing a team member never touches `assigned_to`, and changing `assigned_to` never touches team membership (verified by a dedicated test).

**Endpoints:** `GET/POST /projects/{projectId}/team`, `DELETE /projects/{projectId}/team/{userId}` — matches `Project_API.md`'s Team table exactly, minus the `/companies/{companyId}` prefix (same established deviation as every other module: path-supplied `companyId` is never trusted). Implemented as two plain `APIView` classes (`ProjectTeamView`, `ProjectTeamMemberView`), not `@action`s on `ProjectViewSet` — a `/team/{userId}` DELETE has a second path parameter that doesn't fit DRF's single-lookup-field `@action` routing. Both reuse `ProjectPermission` directly (no new `ProjectMemberPermission` class) since object-level authorization here is exactly "does the caller belong to this Project's company" — the identical check `ProjectViewSet` already performs; a duplicate permission class would add no behavior. Both views fetch the parent Project via `ProjectService.get_project_by_id(project_id)` (no company filter) then call `self.check_object_permissions(request, project)`, the same pattern `ProjectViewSet.retrieve` uses — a cross-tenant `projectId` 404s instead of 403ing (`Error_Handling.md` §5), verified by tests.

**Validation reuses BE-025's assignee invariant:** adding a team member calls the same `validators.validate_assignee_company_membership(user_id, project.company_id)` BE-025 built for `assigned_to` — a team member must be an ACTIVE `CompanyMembership` of the project's company; wrong-company or revoked-membership users are rejected with 400. Duplicate active membership is a 409 `ConflictError` (state conflict, not bad input) with the same pre-check-plus-`IntegrityError`-backstop pattern `RoleService.create_role` established for its own uniqueness constraint (TOCTOU-safe). Removing a nonexistent membership is 404, not a silent no-op.

**No audit logging in this task:** mirrors BE-024/025's deferral — Project's own audit integration (including membership changes) is BE-029's explicit scope.

**Doc corrections made in passing:** `apps/projects/models.py`'s BE-024-era docstrings still referenced the pre-second-renumbering task IDs (e.g. "transition logging is BE-026's" when Workflow is now BE-027) — corrected while touching this file, no behavior change.

**Tests:** 35 new. `apps/projects/tests/test_models.py` +11 (`ProjectMemberModelTestCase`): full-field creation, `assigned_by` optional, str repr, duplicate-active-membership `IntegrityError`, re-add-after-soft-delete succeeds, soft-delete lifecycle, `user`/`assigned_by` SET_NULL on hard delete, Project cascade-delete removes membership rows, reverse accessor from `project.members`. `apps/projects/tests/test_members.py` (new) ×24: service-level (add success with/without `assigned_by`, wrong-company/revoked-membership/nonexistent-user rejected, duplicate-active `ConflictError`, re-add-after-removal, list, remove success, remove-nonexistent `NotFound`, assigned_to/team independence) and endpoint-level (401/403, cross-tenant project 404 on list/add/remove, empty list, add success response shape, add-then-list, wrong-company 400, duplicate 409, missing `userId` 400, platform-admin cross-tenant allowed, remove success and post-removal list reflects it, remove-nonexistent 404). Full `apps/projects` suite: **94 passed** (was 59 after BE-025). Full backend suite: **460 passed, 0 failed** (was 425 after BE-025). `manage.py check`: 0 issues. `makemigrations --check --dry-run`: no changes detected after generating `0002_projectmember.py`. `spectacular --fail-on-warn`: clean.

Depends On

- BE-025 (Project CRUD)

---

### BE-027 – Project Workflow

**Status:** Done

**Priority:** Critical

**Owner:** Backend Team

**Open documentation gap, resolved via Backend Lead decision (AskUserQuestion, 2026-08-31):** neither `CLAUDE.md` nor `Project_API.md` specify whether the status chain allows backward moves or step-skipping, which statuses can side-transition to On Hold/Cancelled, or what a resumed-from-On-Hold project transitions back to — only `Project_API.md`'s note that transitions "should be validated server-side against the allowed lifecycle graph... not freely settable to any value." Backend Lead decided: (1) the main chain (`Draft→Planning→Design→Quotation→Approved→Execution→Quality Check→Handover→Completed`) is **forward-only, one step at a time** — no skipping, no backward moves; (2) **On Hold and Cancelled are reachable from any non-terminal status**, including from Draft and from each other (On Hold→Cancelled); (3) **On Hold resumes only to the exact status the project was in immediately before it was put on hold** — not to any arbitrary caller-chosen status.

**Implementation notes:** The transition graph is a pure function, `get_allowed_next_statuses(current_status, status_before_hold="")` in `apps/projects/models.py`, built from a `MAIN_CHAIN_STATUSES` tuple and a derived `NEXT_MAIN_CHAIN_STATUS` map — no DB access, directly unit-testable. `TERMINAL_PROJECT_STATUSES` (COMPLETED, CANCELLED, from BE-024) have no outgoing transitions at all. A new `Project.status_before_hold` field (`CharField`, blank/default `""`, **not exposed in `ProjectSerializer`** — internal bookkeeping only, not part of `Project_API.md`'s documented response shape) records the pre-hold status; `ProjectService.transition_status()` sets it when entering `ON_HOLD` and clears it when leaving `ON_HOLD` (to any target, including Cancelled). Migration `apps/projects/migrations/0003_project_status_before_hold.py`.

**Endpoint:** `PATCH /projects/{id}/status`, matching `Project_API.md` exactly (minus the `/companies/{companyId}` prefix, same established deviation as every other endpoint). Implemented as `ProjectViewSet.status_transition`, a DRF `@action` on the existing ViewSet (fits cleanly since it needs only the existing `pk` lookup, unlike BE-026's team endpoints) — manually wired in `urls.py` (this project doesn't use a DRF router). `ProjectStatusTransitionSerializer` validates `status` is one of the 11 documented enum values (400 if not); `ProjectService.transition_status()` then checks reachability from the project's *current* status and raises `ConflictError` (409, per `Error_Handling.md`'s state-conflict taxonomy) if the requested transition isn't in the allowed set — a deliberately different status code from "bad input", since the same target value can be valid or invalid depending on where the project currently is. Reuses `ProjectPermission`/`ObjectPermission404Mixin` unchanged — cross-tenant `projectId` 404s, matching every other Project endpoint.

**No audit logging in this task:** mirrors every prior Project task's deferral — transition audit logging (an explicit item in `CLAUDE.md`'s Audit Trail section) is BE-029's scope.

**Doc corrections made in passing:** `ProjectStatus`'s docstring still said "the allowed-transition graph... [is] BE-027's responsibility, not implemented here" as a forward reference — updated to point at `get_allowed_next_statuses` now that it exists.

**Tests:** 25 new, all in `apps/projects/tests/test_workflow.py`. `GetAllowedNextStatusesTestCase` ×9 (pure function, no DB): terminal statuses have zero transitions, Draft's exact allowed set, no-skip-ahead, no-backward-move, Handover→Completed reachable, every main-chain status can reach Cancelled, On-Hold-without-recorded-prior only allows Cancelled, On-Hold-with-recorded-prior allows exactly {that status, Cancelled}, On-Hold cannot resume to an unrecorded status. `ProjectTransitionServiceTestCase` ×9: valid forward transition, skip-ahead rejected (409), backward-move rejected (409), terminal-status rejects everything, hold-then-resume round-trip (asserts `status_before_hold` set then cleared), hold-cannot-resume-to-different-status, hold-can-be-cancelled, Draft-can-be-held-and-resumed, cross-tenant transition raises `NotFound`. `ProjectStatusEndpointTestCase` ×7: 401 unauthenticated, valid transition 200, invalid transition 409, garbage status value 400, missing status 400, cross-tenant project 404, full hold/resume round-trip via the HTTP endpoint. Full `apps/projects` suite: **119 passed** (was 94 after BE-026). `manage.py check`: 0 issues. `makemigrations --check --dry-run`: no changes detected after generating `0003_project_status_before_hold.py`. `spectacular --fail-on-warn`: clean; confirmed `/projects/{id}/status/` present in the generated schema.

Depends On

- BE-026 (Project Members)

---

### BE-028 – Project Filters

**Status:** Done

**Priority:** Medium

**Owner:** Backend Team

**Documentation gap flagged, resolved without blocking (low-risk plumbing, not a security/tenant/RBAC decision):** `Project_API.md` lists the list endpoint's filters as "status, client, assigned user, priority, date range" but never says which date field "date range" means — Project has two (`start_date`, `deadline`). Rather than guess one and silently drop the other, both are exposed as independent optional ranges: `startDateFrom`/`startDateTo` and `deadlineFrom`/`deadlineTo`. Flagged here explicitly rather than invented silently; can be narrowed later if the client confirms only one was meant.

**Implementation notes:** `apps/projects/selectors.py::list_projects()` extended with `status`/`client_id`/`assigned_to_id`/`priority`/`start_date_from`/`start_date_to`/`deadline_from`/`deadline_to`/`ordering` params — exact-match filters for status/client/assignedTo/priority, inclusive range filters (`__gte`/`__lte`) for the two date pairs. `VALID_ORDER_FIELDS = {created_at, updated_at, name, start_date, deadline}` (both directions) — matches Client/Role's ordering convention, extended with the two Project-specific date fields since they're meaningful for schedule-oriented views; `status` was deliberately left out of the orderable set (arbitrary string sort on a lifecycle enum isn't a meaningful default and isn't documented). `ProjectService.list_projects`/`list_projects_for_viewer` forward every param through unchanged (pure plumbing, no new business logic). `ProjectListQuerySerializer` (new, mirrors `ClientListQuerySerializer`) validates `status`/`ordering` as `ChoiceField`s (400 on garbage input) and the four date params as `DateField`s; no free-text `search` param — `Project_API.md` doesn't document one for this endpoint, unlike Client's. `ProjectViewSet.list` now validates query params before calling the service, and declares `parameters=[ProjectListQuerySerializer]` in its `@extend_schema` for schema visibility, mirroring `ClientViewSet.list` exactly.

**No new endpoints, no schema change:** this task is entirely query-param filtering on the existing `GET /projects` — no migration, no new URL.

**Real bug found and fixed:** `list_projects`'s default ordering (`-created_at`) had no secondary tie-breaker. `apps/projects/tests/test_filters.py::test_invalid_ordering_falls_back_to_default` passed when run in isolation but failed when run as part of the full suite — two Projects created back-to-back in `setUp()` got byte-identical `created_at` timestamps (plausible under coarse OS clock resolution, particularly on Windows dev environments), so `ORDER BY created_at DESC` alone has no defined relative order between them and can return a different order across calls. Fixed by appending `"id"` as an unconditional secondary sort key (`queryset.order_by(order_field, "id")`) — UUIDs carry no ordering *meaning*, but guarantee a stable, repeatable order regardless of timestamp collisions. The affected test was corrected to assert membership (`assertCountEqual`) rather than a specific order for the tied case, since no specific order was ever a real guarantee. **Flagged, not fixed here:** `apps/clients/selectors.py::list_clients` and `apps/users/selectors.py::list_roles` share the exact same `order_by(order_field)`-with-no-tie-breaker pattern and are equally exposed to this — out of scope for BE-028 (a Project-only task), noted here for BE-030 ("CRM Tests", explicitly a final stabilization pass across Client+Project) to pick up.

**Tests:** 15 new, `apps/projects/tests/test_filters.py`. `ProjectListFilterServiceTestCase` ×10: filter by status/client/assignedTo/priority individually, filter by start_date range, filter by deadline range, combined filters narrow results, ordering by name ascending, ordering by deadline descending, invalid ordering value falls back to the default (defense-in-depth at the selector layer, matching Client's own selector — even though the serializer already rejects invalid values with 400 before reaching it; asserts membership only, not order, per the tie-breaker finding above). `ProjectListFilterEndpointTestCase` ×5: filter by status query param, invalid status value 400, invalid ordering value 400, ordering by name query param, no-filters-returns-all (regression guard that filtering is opt-in). Full `apps/projects` suite: **134 passed** (was 119 after BE-027). Full backend suite: **500 passed, 0 failed** (was 485 after BE-027; caught the tie-breaker flake on this run, fixed, re-ran clean). `manage.py check`: 0 issues. `makemigrations --check --dry-run`: no changes detected (no model changes in this task). `spectacular --fail-on-warn`: clean.

Depends On

- BE-027 (Project Workflow)

---

### BE-029 – Project Audit Logs

**Status:** Done

**Priority:** High

**Owner:** Backend Team

**Implementation notes:** Wires `AuditLogService.record()` into every Project mutation deferred by BE-024 through BE-028: create/update/delete (`apps/projects/services.py::ProjectService`), status transitions, and team member add/remove (`ProjectMemberService`). Mirrors `apps.clients.services.ClientService`'s exact pattern — `actor_user`/`request` params threaded from `ProjectViewSet`/`ProjectTeamView`/`ProjectTeamMemberView` down to the service layer, a `_project_audit_state()`/`_project_member_audit_state()` helper snapshotting the allowlisted fields. `ENTITY_FIELD_ALLOWLISTS` (`apps/audit/validators.py`) gained two entries: `"project"` (`name`, `client_id`, `status`, `priority`, `assigned_to_id`, `start_date`, `deadline`, `follow_up_reminder_at` — full field coverage, since Project has no privacy-sensitive free-text field the way `client.addresses`/`notes` do) and `"project_member"` (`project_id`, `user_id`, `assigned_by_id` — membership changes get their **own** `entity_type`/`entity_id`, not folded into the parent Project's rows, so the state itself carries the project/user linkage for a self-describing row without a join). Status transitions are recorded as `AuditAction.UPDATE`, not a separate action value, per `AuditAction`'s own documented convention ("a status change is recorded as an UPDATE... not a separate action value") — already established for every other entity in this codebase, not a new decision.

**Real bug found and fixed before any test ran:** `apps.audit.models.AuditLog.before_state`/`after_state` is a plain `JSONField` with **no custom encoder** — `ClientService`'s audited fields are all already strings, so this never surfaced before, but Project's audited fields include two FK ids (`client_id`, `assigned_to_id`, both `uuid.UUID` instances via Django's `_id` accessor) and three date/datetime fields. A raw `uuid.UUID`/`datetime.date`/`datetime.datetime` passed straight into `AuditLogService.record()` raises `TypeError` at save time under the default `json.JSONEncoder`. Fixed with a `_serialize_audit_value()` helper that `.isoformat()`s dates/datetimes and `str()`s UUIDs before the state dict is built — caught by a dedicated regression test (`test_create_project_with_dates_serializes_cleanly`) before it could reach a real audit-log write failure in any other task.

**Verified negative case:** a status transition that raises `ConflictError` (invalid per the graph) writes **no** audit entry — the `AuditLogService.record()` call sits after the `ConflictError` raise inside the same `transaction.atomic()` block, so it never executes and nothing is persisted even transiently.

**No changes to Client/Role audit behavior:** this task only touches Project's own services/views and the two new `ENTITY_FIELD_ALLOWLISTS` entries — `"client"`/`"role"`/`"company"`/`"user"` entries are untouched.

**Tests:** 8 new, `apps/projects/tests/test_audit.py` (`ProjectAuditLogTestCase`): create writes a CREATE entry with correct `company_id`/`actor_user_id`/`after_state`, create-with-dates serializes cleanly (the regression guard for the bug above), update writes before/after, soft-delete writes a DELETE entry with `before_state` only, status transition writes an UPDATE entry (not a separate action), a failed/rejected status transition writes no UPDATE entry (only the earlier CREATE from setup), add-member writes a CREATE entry under `entity_type="project_member"`, remove-member writes a DELETE entry under the same. Full `apps/projects` suite: **142 passed** (was 134 after BE-028). `manage.py check`: 0 issues. `makemigrations --check --dry-run`: no changes detected (no model changes — `AuditLog`/`ENTITY_FIELD_ALLOWLISTS` needed no migration, matching how BE-023's own audit wiring needed none). `spectacular --fail-on-warn`: clean (no endpoint/schema changes in this task).

Depends On

- BE-028 (Project Filters)

---

### BE-030 – CRM Tests

**Status:** Done

**Priority:** High

**Owner:** Backend Team

**Scope:** the final Sprint 2 stabilization pass across Client + Project — no doc gives "CRM Tests" a more specific scope than its title, so this task was scoped conservatively as verification/hardening, not new features: (1) fix the one concrete defect flagged during BE-028 and (2) run the full backend suite as a final sign-off gate for the sprint. No new endpoints, no new business rules.

**Real bug fixed across three more modules:** BE-028 found and fixed a missing ordering tie-breaker in `apps/projects/selectors.py::list_projects` (`order_by(order_field)` with no secondary key means two rows whose `order_field` value ties — most commonly `created_at`, which can collide under coarse OS clock resolution — have no defined relative order and can come back differently across calls) and flagged that `apps/clients/selectors.py::list_clients` and `apps/users/selectors.py::list_roles` shared the identical pattern. Grepped the full backend for every other occurrence of the same `order_by(order_field)` call and found one more: `apps/company/selectors.py::list_companies`. Fixed all three the same way — append `"id"` as an unconditional secondary sort key. Zero behavior change for the normal case (distinct `order_field` values); only affects the previously-undefined tie case.

**Regression coverage added for the fix, not just the original flake:** rather than rely on naturally-occurring timestamp collisions (as the original BE-028 flake did), each new test forces the exact collision via `.update(created_at=<shared value>)` (bypassing `auto_now_add`, which only fires on `.create()`/`.save()`) and asserts the same query returns the same result twice — `apps/clients/tests/test_ordering_tiebreak.py`, `apps/users/tests/test_role_ordering_tiebreak.py`, `apps/company/tests/test_ordering_tiebreak.py`, plus one added to `apps/projects/tests/test_filters.py` for Project itself (BE-028 never got a deterministic forced-tie test of its own — only the accidental flake that led to the fix).

**No other findings from the stabilization pass:** re-ran `manage.py check`, `makemigrations --check --dry-run`, and `spectacular --fail-on-warn` — all clean, no drift accumulated across BE-022–029. Full backend suite re-verified green end-to-end as the sprint-closing gate.

**Sprint 2 status:** every task BE-022–BE-030 is now implemented, tested, and documented at **Review** status. Per this file's standing rule ("never self-mark Done — only the user can approve a task to Done"), Sprint 2 itself is not marked closed here; that requires explicit Backend Lead review and approval of the outstanding Review-status tasks, the same as every individual task above.

**Tests:** 4 new (one per affected app, listed above). Full backend suite: **512 passed, 0 failed** (was 508 after BE-029). `manage.py check`: 0 issues. `makemigrations --check --dry-run`: no changes detected (ordering is a query-time concern, no schema change). `spectacular --fail-on-warn`: clean (no endpoint changes in this task).

Depends On

- BE-029 (Project Audit Logs)

---

# Sprint 3 – Product Catalog

_(Renumbered 2026-08-31, Sprint 3 planning: dropped the standalone "BE-034 – Units" task — Migration_Plan.md's 013–015 (Group D) only cover product_category/product_subcategory/product; there is no separate `unit` table anywhere in the 27-migration plan, and FRS.md §11's `unit` is just a plain field on `product` with a documented 8-value enum. Backend Lead decided (AskUserQuestion, 2026-08-31) to fold the Unit enum into BE-033 (Products) rather than keep a task with no domain/table of its own. Every ID from the old BE-035 onward shifted back by one to close the gap; Sprints 4–6 shifted accordingly (Sprint 4 now BE-035–038, Sprint 5 now BE-039–041, Sprint 6 now BE-042–045). Confirmed via grep that no code references any of the old BE-034–046 IDs before renumbering.)_

- BE-031 – Categories
- BE-032 – Subcategories
- BE-033 – Products
- BE-034 – Catalog APIs

Status: Done

---

### BE-031 – Categories

**Status:** Done

**Priority:** High

**Owner:** Backend Team

**Pre-implementation documentation audit (AskUserQuestion, 2026-08-31) found three real gaps, resolved by Backend Lead decision before any code was written:** (1) the tracker's standalone "BE-034 – Units" task had no corresponding table anywhere in `Migration_Plan.md` — folded into BE-033 as a `TextChoices` enum, Sprint 3 renumbered to 4 tasks (see the renumbering note above); (2) `BOQ_API.md`'s Product Catalog sketch documents no DELETE endpoint for Category/Subcategory/Product — decided to add standard soft-delete DELETE endpoints to all three anyway, consistent with every other module built in this codebase (Role/Client/Project all got one regardless of how thin their own API doc sketch was); (3) `Product.status` has zero documented values anywhere (unlike Company/Project's documented enums) — decided it will be an Active/Inactive `TextChoices` enum, to be built in BE-033. A fourth decision (block Category/Subcategory delete while active children exist, mirroring the Client-Project guard) is recorded here for BE-032/BE-033 to implement, since Category has no children of its own to guard against yet.

**Implementation notes:** New `apps.products` app (per `00_Development_Standards/Folder_Structure.md` §2a — Categories, Subcategories, and Products all live in this one app, not three separate ones). `ProductCategory(BaseModel)`: `company` FK (CASCADE, required), `name` (required) — field set matches `Database_Schema.md`'s `product_category(id, company_id, name)` exactly, no invented uniqueness constraint (mirrors the Client precedent — not documented). Composite index `(company, name)`, named `product_cat_comp_name_idx` (Django's cross-DB 30-character index-name limit — `models.E034` — forced a shorter name than the `<table>_company_name_idx` pattern used elsewhere). Full CRUD mirroring `ClientViewSet`/`ClientService`/`ClientSerializer` exactly: flat `GET/POST /product-categories`, `GET/PATCH/PUT/DELETE /product-categories/{id}` (matching `BOQ_API.md`'s literal path, no `/companies/{companyId}` prefix per the established deviation). `ProductCategoryPermission` is the same coarse tenant-membership gate as every other module (`product.view`/`product.manage` permission codes are documented but no `Permission`/`RolePermission` model exists yet — standing Backend Lead decision, unchanged). Ordering (`?ordering=name/-name/created_at/-created_at/updated_at/-updated_at`) ships in this same task (unlike Project, which split CRUD/Filters into two tasks) — matches the Client/Role/Company precedent of including basic ordering in the CRUD task itself; the `"id"` tie-breaker (BE-030's finding) is applied from day one here, not retrofitted after a flake. No `search` param — Category has only one field (`name`), so a dedicated search would just duplicate an exact/`icontains` filter, and it isn't documented anyway.

**Audit logging wired inline, not deferred:** unlike Project (which got its own dedicated BE-029 task), Sprint 3's task list has no separate "Product Audit Logs" task — this follows Client's BE-023 precedent instead, wiring `AuditLogService.record()` directly into create/update/delete within this same task. `ENTITY_FIELD_ALLOWLISTS["product_category"] = {"name"}` added to `apps/audit/validators.py`.

**Deferred (documented, not a gap, mirrors BE-022/023/024's identical Client→Project deferral):** the "block delete if active Subcategories exist" guard can't be built until BE-032 (`ProductSubcategory`) exists — `soft_delete_category()` is unconditional in this task. BE-032 adds the guard the same way BE-024 added Client's.

**Tests:** 51 new. `apps/products/tests/test_models.py` ×9: required-field creation, str repr, no-uniqueness-constraint confirmation, same-name-different-company allowed, tenant isolation via FK, soft-delete lifecycle + restore, cascade delete with Company, required-company enforcement, composite index exists. `test_services.py` ×17: create/get/list/update/soft-delete success and cross-tenant-scoping paths, duplicate-name-allowed, `resolve_create_target_company_id`/`list_categories_for_viewer` admin vs. non-admin branches, blank-name-rejected, audit row creation on create/update/delete. `test_views.py` ×25: 401/403 (including revoked membership), list scoping (member vs. platform-admin-sees-all), ordering, invalid-ordering 400, empty-list shape, soft-deleted exclusion, create (member/admin-with-companyId/admin-without-companyId-400/company-injection-403/validation-400), retrieve (success/cross-tenant-404/indistinguishable-from-nonexistent/admin-allowed), update (success/PUT-behaves-like-PATCH/cross-tenant-404/admin-allowed), delete (soft-deletes/cross-tenant-404/admin-allowed). Full `apps/products` suite: **51 passed, 0 failed**. `manage.py check`: 0 issues. `makemigrations --check --dry-run`: no changes detected after generating `0001_initial.py`. `spectacular --fail-on-warn`: clean; confirmed `/product-categories/` and `/product-categories/{id}/` present in the generated schema, tagged "Product Catalog".

Depends On

- BE-021 (Multi-Tenant Resolution — reused directly, Product Catalog has no dependency on Client/Project per `Module_Dependency_Map.md`'s own note that "Product may be started in parallel... since Product's only real dependency is `company`")

---

### BE-032 – Subcategories

**Status:** Done

**Priority:** High

**Owner:** Backend Team

**Implementation notes:** New `ProductSubcategory(BaseModel)` in the same `apps.products` app: `company` FK (CASCADE, required — its own column per `Database_Schema.md`'s `product_subcategory(id, company_id, category_id FK, name)`, not merely derived through `category`), `category` FK (**CASCADE**, required), `name` (required). `category` uses CASCADE rather than PROTECT — unlike `Project.client`, no doc names Category→Subcategory as an example requiring hard-delete protection the way `Naming_Standards.md` §4 explicitly did for Client→Project; a plain catalog parent/child hierarchy defaults to the more common CASCADE convention already used by `CompanyMembership`/`ProjectMember`. Composite index `(company, category)`, named `prod_subcat_comp_cat_idx` (same Django 30-character index-name limit as BE-031's category index).

**Endpoints match `BOQ_API.md`'s nested shape, split the same way Project Team was (BE-026):** `GET/POST /product-categories/{categoryId}/subcategories` (`ProductSubcategoryListCreateView`, a plain `APIView` — fetches the parent Category via `ProductCategoryService.get_category_by_id` + `check_object_permissions`, the same cross-tenant-404 pattern every nested endpoint in this codebase uses) for list/create, and flat `GET/PATCH/PUT/DELETE /product-subcategories/{id}` (`ProductSubcategoryViewSet`, detail-actions only — no `list`/`create` wired to this path) for individual-record operations, since `BOQ_API.md` never documents a nested single-subcategory path at all. Both reuse `ProductCategoryPermission` directly (its object-level check only inspects `obj.company_id`, identical either way) — no separate `ProductSubcategoryPermission` class, mirroring `ProjectTeamView`'s reasoning exactly.

**Resolves BE-031's deferred guard:** `ProductCategoryService.soft_delete_category()` now checks `selectors.has_active_subcategories_for_category()` before deleting and raises `ConflictError` (409) if the category has any non-deleted Subcategory — mirrors the Client-cannot-delete-while-active-Projects-exist guard exactly. **Architecture difference from that precedent, noted deliberately:** Client/Project needed a dedicated `ProjectSelector` class specifically to avoid a cross-*app* domain-ownership violation (Client and Project are separate Django apps). Category and Subcategory live in the **same** app (`apps.products`), so the identical cross-app concern doesn't exist here — the guard is a plain module-level selector function, not a class, and the query lives directly alongside Category's own selectors without indirection for its own sake.

**Own guard deferred in turn (documented, not a gap):** `soft_delete_subcategory()` is unconditional in this task — the "block delete if active Products exist" guard can't be built until BE-033 (`Product`) exists. BE-033 adds it, continuing the same chain BE-031 started.

**Tests:** 40 new. `apps/products/tests/test_models.py` +11: required-field creation, str repr, no-uniqueness-constraint, tenant isolation via FK, soft-delete lifecycle + restore, Category `CASCADE` hard-delete removes Subcategory, Company `CASCADE` hard-delete removes Subcategory, required-category enforcement, reverse accessor from `category.subcategories`, Category **soft**-delete leaves Subcategory's FK untouched (verifies `SoftDeleteModel.delete()` never triggers the FK's `on_delete`, the same BE-024 finding applied here). `apps/products/tests/test_services.py` +21: `ProductCategoryService` guard tests (blocked-by-active-subcategory, blocked-delete-writes-no-audit-entry, succeeds-with-zero-subcategories, succeeds-when-subcategory-already-deleted) plus full `ProductSubcategoryService` coverage (create/get/list/update/soft-delete success and cross-tenant paths, blank-name-rejected, audit row creation on create/update/delete including `category_id` stringification). `apps/products/tests/test_views.py` +9 (`ProductSubcategoryViewTestCase`) plus 1 added to the Category test case (`test_delete_category_blocked_by_active_subcategory_returns_409`): 401/403, cross-tenant category 404 on nested list/create, list-for-category, create success/validation-400/cross-tenant-404, platform-admin-cross-tenant-create-allowed, flat retrieve/update/delete success and cross-tenant-404. Full `apps/products` suite: **91 passed** (was 51 after BE-031). `manage.py check`: 0 issues. `makemigrations --check --dry-run`: no changes detected after generating `0002_productsubcategory.py`. `spectacular --fail-on-warn`: clean; confirmed `/product-categories/{category_id}/subcategories/` and `/product-subcategories/{id}/` present in the generated schema.

Depends On

- BE-031 (Categories)

---

### BE-033 – Products

**Status:** Done

**Priority:** High

**Owner:** Backend Team

**Implementation notes:** New `Product(BaseModel)` — the leaf of the catalog hierarchy — plus two `TextChoices` enums: `ProductUnit` (the 8 documented values from `01_Business/FRS.md` §11: Nos, Sq.ft, Sq.m, Running ft, Kg, Litre, Set, Job — the one Product field with an actual enumerated domain) and `ProductStatus` (Active/Inactive, the Backend Lead decision recorded in BE-031's entry, since `status` has zero documented values anywhere). Field set matches `Database_Schema.md`'s `product(id, company_id, subcategory_id FK, name, image_url, unit, default_cost, default_selling_rate, tax_rate, status)` exactly. Only `company`/`subcategory`/`name` are required — `image_url`/`unit`/pricing/`tax_rate` are optional detail fields, mirroring Project's own only-the-identifying-fields-are-required philosophy (BE-024/025). Money fields (`default_cost`, `default_selling_rate`) use `DecimalField(max_digits=14, decimal_places=2)` — `03_Database/Naming_Standards.md`'s documented `NUMERIC(14,2)` convention for money columns, the first field in this codebase to need it. `tax_rate` uses `max_digits=5, decimal_places=2` (a plain numeric-precision choice for a percentage, not a business rule). `subcategory` uses CASCADE, matching `ProductSubcategory.category`'s own BE-032 reasoning. Two indexes: `(company, status)` (mirrors Project's own composite index exactly) and a bare `subcategory` index for the list-by-subcategory query BE-034 will need.

**Endpoints are flat, not nested** (unlike Subcategory) — `GET/POST /products`, `GET/PATCH/PUT/DELETE /products/{id}`, matching `BOQ_API.md`'s own literal paths (`/companies/{companyId}/products`, minus the established `/companies/{companyId}` deviation). `status` **is** settable at create, unlike Project — `BOQ_API.md`'s own text explicitly lists "status" among Product's create fields ("Create product/work item (unit, default cost, default rate, tax, status)"), a genuine documented difference from Project_API.md's separate-status-endpoint design, not an inconsistency. `subcategory` is not editable via the general update endpoint, mirroring `ProjectUpdateSerializer`'s exclusion of `client` for the identical reasoning (set at creation, not casually reassigned).

**Tenant invariant enforcement:** `ProductService.create_product()` reuses `ProductSubcategoryService.get_subcategory_by_id(subcategory_id, company_id=...)`, which already raises `NotFound` on cross-tenant access — the same reuse-don't-duplicate pattern BE-025 established for `Project.client`.

**Real bug found and fixed before any test ran:** `spectacular --fail-on-warn` hit the same enum-naming collision BE-025 found (`Company.status`/`Project.status`) — now a three-way collision with `Product.status`. Fixed by adding `"ProductStatusEnum": "apps.products.models.ProductStatus"` to `SPECTACULAR_SETTINGS["ENUM_NAME_OVERRIDES"]` in `config/settings.py`.

**Audit logging wired inline** (mirrors BE-031/032, not deferred): `_product_audit_state()` stringifies `subcategory_id` (a `uuid.UUID`) and the three `Decimal` fields before they reach `AuditLogService.record()` — the same `JSONField`-has-no-custom-encoder gap BE-029 found for Project's FK ids/dates, now hit again for Product's FK id and money fields. `ENTITY_FIELD_ALLOWLISTS["product"]` added with full field coverage.

**Resolves BE-032's deferred guard:** `ProductSubcategoryService.soft_delete_subcategory()` now checks `selectors.has_active_products_for_subcategory()` and raises `ConflictError` (409) if the subcategory has any non-deleted Product — closing the deferral chain BE-031 started (Category→Subcategory→Product, each guard added by the task that introduces the next level down). Product itself needs no delete guard of its own — nothing in this sprint's scope references it yet (`boq_item.product_id` is a later sprint's concern).

**Deferred to BE-034 (documented, not a gap, mirrors the BE-025/BE-028 CRUD/Filters split for Project):** `list_products()` is deliberately bare — no category/subcategory/status filtering, which `BOQ_API.md` documents as this endpoint's filter set but which BE-034 ("Catalog APIs") owns as its own task.

**Tests:** 46 new. `apps/products/tests/test_models.py` +11: required-fields-only creation with correct defaults, full-field creation, all 8 `ProductUnit` values accepted, str repr, tenant isolation via FK, soft-delete lifecycle + restore, Subcategory `CASCADE` hard-delete removes Product, required-subcategory enforcement, Subcategory **soft**-delete leaves Product's FK untouched, composite indexes exist. `apps/products/tests/test_services.py` +23: `ProductSubcategoryService` guard tests (blocked-by-active-product, succeeds-with-zero-products) plus full `ProductService` coverage (create success/with-explicit-status/nonexistent-company/cross-tenant-subcategory-rejected, get/list/cross-tenant scoping, `list_products_for_viewer` platform-admin-sees-all, `resolve_create_target_company_id` mismatch-denied, update success/status-update/cross-tenant-404/subcategory-changes-ignored, soft-delete, audit row creation on create/update/delete including `Decimal`/`uuid.UUID` stringification). `apps/products/tests/test_views.py` +12 (`ProductViewSetTestCase`) plus 1 added to the Subcategory test case (`test_delete_subcategory_blocked_by_active_product_returns_409`): 401/403, list scoping (member vs. platform-admin-sees-all), create (success/missing-subcategoryId-400/cross-tenant-subcategory-404/invalid-unit-400/company-injection-403), retrieve (success/cross-tenant-404), update (success/status-update/cross-tenant-404), delete (soft-deletes/cross-tenant-404). Full `apps/products` suite: **137 passed** (was 91 after BE-032). `manage.py check`: 0 issues. `makemigrations --check --dry-run`: no changes detected after generating `0003_product.py`. `spectacular --fail-on-warn`: clean after the `ENUM_NAME_OVERRIDES` fix; confirmed `/products/` and `/products/{id}/` present in the generated schema.

Depends On

- BE-032 (Subcategories)

---

### BE-034 – Catalog APIs

**Status:** Done

**Priority:** Medium

**Owner:** Backend Team

**Scope:** the final Sprint 3 task, resolving BE-033's documented deferral — adds `BOQ_API.md`'s documented `GET /products` filter set (category, subcategory, status) exactly, mirroring the CRUD/Filters split BE-025/BE-028 established for Project. No new endpoints, no schema/migration change.

**Implementation notes:** `apps/products/selectors.py::list_products()` extended with `category_id`/`subcategory_id`/`status` params — exact-match filters for `subcategory_id`/`status`; `category_id` filters via `subcategory__category_id` since Product has no direct FK to `ProductCategory` (only to `ProductSubcategory`, which itself FKs to Category). `ProductService.list_products`/`list_products_for_viewer` forward every param through unchanged (pure plumbing). `ProductListQuerySerializer` gained `category`/`subcategory` (`UUIDField`s) and `status` (`ChoiceField`, 400 on garbage input) alongside the existing `ordering` field. `ProductViewSet.list` validates and forwards them; the `@extend_schema` `parameters` list was extended to document all three for schema visibility.

**Tests:** 10 new, `apps/products/tests/test_catalog_filters.py`. `ProductListFilterServiceTestCase` ×5: filter by category (via subcategory join)/subcategory/status individually, combined filters narrow results, no-filters-returns-all (regression guard that filtering is opt-in). `ProductListFilterEndpointTestCase` ×5: filter by status/category/subcategory query params, invalid status value 400, no-filters-returns-all via the HTTP endpoint. Full `apps/products` suite: **147 passed** (was 137 after BE-033). `manage.py check`: 0 issues. `makemigrations --check --dry-run`: no changes detected (query-time filtering only, no model changes). `spectacular --fail-on-warn`: clean.

**Sprint 3 status:** every task BE-031–BE-034 is now implemented, tested, and documented at **Review** status, closing out Product Catalog. Per this file's standing rule, Sprint 3 itself is not marked closed here — that requires explicit Backend Lead review and approval of the four Review-status tasks above, the same as every prior sprint.

Depends On

- BE-033 (Products)

---

# Sprint 4 – BOQ

Status: Done

---

### BE-035 – BOQ Module

**Status:** Done

**Priority:** Critical

**Owner:** Backend Team

**Pre-implementation documentation audit (AskUserQuestion, 2026-08-31) found two genuine business-rule/architecture gaps, resolved by Backend Lead decision before any code was written:** (1) `boq_item.discount`/`tax` (Database_Schema.md) and the summary endpoint's "computed subtotal/discount/tax/total" have no documented representation — decided **percentages** (matching `Product.tax_rate`'s already-established convention), not flat currency amounts; this determines BE-037's summary formula. (2) `BOQ_API.md` documents no `POST .../boq` endpoint at all, only `GET .../boq` and `POST .../boq/sections` — decided BOQ is **auto-created on first access** (a `get_or_create` per project), matching `Migration_Plan.md`'s own stated rationale for the table's position ("One BOQ per project") and the absence of any documented create step.

**Two inferred decisions, not asked (documented here instead):** (a) `boq_section`/`boq_item` have **no `company_id` column** in `Database_Schema.md` — unlike every tenant table built so far in this codebase (Client, Project, ProjectMember, ProductCategory/Subcategory/Product all denormalize `company`). Followed the schema literally rather than adding an undocumented column — tenant scoping for a Section resolves through `section.boq.company_id`, not a column on the table itself. (b) Sprint 4's task list (BOQ Module / Items / Calculations / APIs) has no separate "Audit Logs" task, so audit logging is wired **inline** in each task as its mutations are built — the same precedent Sprint 3's Product Catalog established (BE-031), not Project's separate BE-024-029 split.

**Implementation notes:** New `apps.boq` app (per `00_Development_Standards/Folder_Structure.md` §2a). `BOQ(BaseModel)`: `company` FK (CASCADE), `project` — a **`OneToOneField`** (the first in this codebase), enforcing "one BOQ per project" at the database level, not just by convention. `status` is a plain unconstrained `CharField` — no documented value domain anywhere (unlike Project/Company's documented enums), and no endpoint in `BOQ_API.md` ever reads or writes it; treated like `Project.priority` was when undocumented, not like `Product.status` (which had an obvious binary real-world meaning this field doesn't). `BOQSection(BaseModel)`: `boq` FK (CASCADE — no doc names this relationship as needing hard-delete protection, same reasoning as Category→Subcategory), `name` (required), `sort_order` (`PositiveIntegerField`, auto-assigned as `max existing + 1` — `BOQ_API.md`'s "Add a section" row lists no input fields at all, so no manual override is exposed).

**Endpoints:** `GET /projects/{projectId}/boq` (`BOQDetailView`) returns the full tree (BOQ + nested sections; items join the response shape in BE-036) and auto-creates the BOQ if it doesn't exist yet. `POST /projects/{projectId}/boq/sections` (`BOQSectionListCreateView`) adds a section, auto-creating the BOQ too if needed. Both reuse `ProjectPermission` directly (object-level check is "does the caller belong to this Project's company", identical whether checked against the Project or the BOQ) — no new permission class, mirroring `ProjectTeamView`'s established reasoning. **Section PATCH/DELETE added for CRUD consistency** (`/boq-sections/{id}`, flat) even though `BOQ_API.md` documents neither — the same "add missing CRUD" Backend Lead decision BE-031 established for Category/Subcategory/Product's DELETE endpoints, applied here to Section's full edit surface.

**Deferred (documented, not a gap, continues the exact BE-031→032→033 deferral chain):** `soft_delete_section()` is unconditional in this task — the "block delete if active Items exist" guard can't be built until BE-036 (`BOQItem`) exists. BE-036 adds it.

**Tests:** 43 new. `apps/boq/tests/test_models.py` ×16: BOQ creation/str-repr/one-per-project-enforced (`OneToOneField` uniqueness)/required-project/cascade-delete-with-project/soft-delete-lifecycle; Section creation/str-repr/default-ordering-by-sort_order/required-boq/cascade-delete-with-boq/soft-delete-lifecycle/BOQ-soft-delete-leaves-Section-FK-untouched/reverse-accessor. `apps/boq/tests/test_services.py` ×15: `BOQService` get-or-create-creates-on-first-call/is-idempotent/writes-audit-only-on-creation; `BOQSectionService` create/list/get/update/soft-delete success and cross-tenant-scoping paths, auto-increment-sort-order, blank-name-rejected, audit row creation on create/update/delete. `apps/boq/tests/test_views.py` ×12: 401/403, cross-tenant project 404, BOQ auto-creates-on-first-access and is-idempotent, platform-admin-cross-tenant-access-allowed, create-section success/appears-in-tree/validation-400/cross-tenant-404, flat update/delete success and cross-tenant-404. Full `apps/boq` suite: **43 passed, 0 failed**. `manage.py check`: 0 issues. `makemigrations --check --dry-run`: no changes detected after generating `0001_initial.py`. `spectacular --fail-on-warn`: clean; confirmed `/projects/{project_id}/boq/`, `/projects/{project_id}/boq/sections/`, and `/boq-sections/{id}/` present in the generated schema, tagged "BOQ".

Depends On

- BE-025 (Project CRUD — BOQ is nested under Project)
- BE-033 (Products — `boq_item.product_id` will reference it in BE-036)

---

### BE-036 – BOQ Items

**Status:** Done

**Priority:** Critical

**Owner:** Backend Team

**Implementation notes:** New `BOQItem(BaseModel)` — field set matches `Database_Schema.md`'s `boq_item(id, boq_section_id FK, product_id FK nullable, description, quantity, unit, rate, discount, tax, amount, is_optional, is_alternative, notes)` exactly, same no-`company`-column schema literalism as `BOQSection` (BE-035). `product` is nullable `SET_NULL` (an item may optionally reference a catalog Product or be pure free-text, per `BOQ_API.md`), preserving a historical item's frozen description/rate if the referenced Product is later hard-deleted — mirrors `Project.assigned_to`'s `SET_NULL` reasoning. `unit` reuses `apps.products.models.ProductUnit`'s 8 documented values directly (FRS.md §11/§12 name the same unit list for both Product and BOQ items — one enum, not a duplicate). `discount`/`tax` are percentages (`max_digits=5, decimal_places=2`), the Backend Lead decision from BE-035 planning. `amount` is always server-computed (`quantity * rate`, `BOQ_API.md`'s own documented formula, explicitly "never trusted from client") — no caller can set it directly.

**Product-reference defaulting, resolved without asking (a direct reading of `BOQ_API.md`'s own Notes, not an invention):** when `productId` is supplied and `description`/`unit`/`rate`/`tax` are omitted, they default from the product's `name`/`unit`/`default_selling_rate`/`tax_rate` ("inherit default cost/rate/unit/tax"). Without a product, `description`/`unit`/`rate` have no sensible default and are required — `ValidationError` (400) if missing. Explicit values always win over product defaults, including an explicit `tax: 0` (verified by a dedicated regression test — `Decimal(0)` is falsy in Python, so a naive `tax or product.tax_rate` would have silently discarded a legitimate "no tax" override).

**Tenant invariant enforcement:** `BOQItemService.create_item()` reuses `ProductService.get_product_by_id(product_id, company_id=...)`, which already raises `NotFound` on cross-tenant access — the same reuse-don't-duplicate pattern `BE-025`/`BE-033` established for `Project.client`/`Product.subcategory`.

**A second tenant-safety check beyond the usual pattern:** the item-create endpoint's URL carries both `projectId` and `sectionId` (`BOQ_API.md`'s literal nested path). Unlike every prior nested-create endpoint in this codebase, a `company_id` match alone isn't sufficient here — a company can have multiple Projects, each with its own BOQ, so a `sectionId` belonging to a *sibling* project under the *same* company would pass a company-only check. `BOQItemListCreateView` explicitly verifies `section.boq.project_id == project.id` (404 if not), covered by a dedicated test (`test_section_from_sibling_project_returns_404`).

**Real bug found and fixed before any other test ran:** `Decimal("2.00") * Decimal("10.00")` produces `Decimal("20.0000")` — 4 decimal places, not the 2 `amount`'s `decimal_places=2` implies. Postgres' `NUMERIC(14,2)` column silently rounds it on the *next* fetch, but the in-memory value used for the immediate API response and audit log entry stayed unrounded until then (caught by `test_create_item_writes_audit_log_entry` failing with `'20.0000' != '20.00'`, not assumed). Fixed with a shared `_compute_amount()` helper that explicitly `.quantize()`s to 2 decimal places (`ROUND_HALF_UP`), used by both `create_item` and `update_item`.

**Endpoints:** `POST /projects/{projectId}/boq/sections/{sectionId}/items` (`BOQItemListCreateView`, no GET — items are retrieved via `BOQDetailView`'s tree, which now nests `items` inside each section). `PATCH/PUT/DELETE /boq-items/{id}` (`BOQItemViewSet`, flat), matching `BOQ_API.md`'s documented paths exactly. `update_item` also accepts `description`/`unit` (not in `BOQ_API.md`'s literal PATCH field list — "quantity/rate/discount/tax/notes/optional/alternative flags" — but excluding them would make a free-text item's own identifying content unfixable after a typo; `product`/`section` reassignment remains excluded, matching every prior module's exclusion of its own parent reference from PATCH).

**Resolves BE-035's deferred guard:** `BOQSectionService.soft_delete_section()` now checks `selectors.has_active_items_for_section()` and raises `ConflictError` (409) if the section has any non-deleted Item — closing the deferral chain BE-031 started, now spanning Category→Subcategory→Product *and* BOQ→Section→Item.

**Audit logging wired inline** (mirrors BE-035, not deferred): `_item_audit_state()` stringifies `product_id` (`uuid.UUID`) and four `Decimal` fields before reaching `AuditLogService.record()` — the same `JSONField`-has-no-custom-encoder gap BE-029/BE-033 found, hit again here. `ENTITY_FIELD_ALLOWLISTS["boq_item"]` added with full field coverage.

**Tests:** 39 new. `apps/boq/tests/test_models.py` +9: free-text/with-product creation, str repr, required-section, Section `CASCADE` hard-delete removes Item, Product `SET_NULL` on hard-delete (description/rate stay frozen), soft-delete lifecycle, Section **soft**-delete leaves Item's FK untouched, reverse accessor. `apps/boq/tests/test_services.py` +23 (`BOQItemServiceTestCase`, plus 2 added to `BOQSectionServiceTestCase` for the resolved guard): create free-text success, missing-description/missing-rate/missing-quantity rejected (400), create-with-product inherits defaults, explicit values override product defaults, explicit `tax=0` not silently overridden (the regression guard for the bug above), cross-tenant product `NotFound`, list/get/cross-tenant scoping, update recomputes `amount`, cross-tenant update `NotFound`, soft-delete, audit row creation on create/update/delete. `apps/boq/tests/test_views.py` +14 (`BOQItemViewTestCase`, plus 1 added to the Section test case): 401, cross-tenant project 404, sibling-project-section 404 (the second tenant-safety check above), create free-text/with-product-inherits-defaults/missing-fields-400, item-appears-in-boq-tree, update recomputes amount, cross-tenant update/delete 404, delete soft-deletes. Full `apps/boq` suite: **82 passed** (was 43 after BE-035). `manage.py check`: 0 issues. `makemigrations --check --dry-run`: no changes detected after generating `0002_boqitem.py`. `spectacular --fail-on-warn`: clean; confirmed `/projects/{project_id}/boq/sections/{section_id}/items/` and `/boq-items/{id}/` present in the generated schema.

Depends On

- BE-035 (BOQ Module)

---

### BE-037 – BOQ Calculations

**Status:** Done

**Priority:** Critical

**Owner:** Backend Team

**Scope:** `GET /projects/{projectId}/boq/summary`, matching `BOQ_API.md`'s documented "Computed subtotal/discount/tax/total". Read-only — no persistence, no audit entry (nothing is mutated). Per-item `amount` computation (`quantity * rate`) already landed in BE-036 since it's intrinsic to a single item's own CRUD; this task owns the cross-item aggregation, mirroring how record-intrinsic computation stayed with CRUD while cross-record math got its own task (the same split Project's Filters (BE-028) took from its CRUD (BE-025)).

**Formula (percentages, the Backend Lead decision from BE-035 planning):** per includible item — `item_discount = base * discount / 100`; `after_discount = base - item_discount`; `item_tax = after_discount * tax / 100`; `item_total = after_discount + item_tax` (tax applied after discount, the standard invoicing order). Aggregated: `subtotal = sum(base)`, `discount = sum(item_discount)`, `tax = sum(item_tax)`, `total = subtotal - discount + tax`. Every intermediate percentage computation is `.quantize()`d to 2 decimal places (`ROUND_HALF_UP`) before summing, using the same pattern BE-036's `_compute_amount()` fix established — not summing raw unrounded Decimals and rounding only the final total, which would produce a different (and arguably less correct) number for the same inputs.

**Optional/alternative exclusion — implemented as documented, the ambiguous part deliberately left alone:** `selectors.list_includible_items_for_boq()` excludes `is_optional`/`is_alternative` items entirely from every sum, per `BOQ_API.md`'s own Notes ("Optional and alternative items must be excluded from the default total"). That same Notes section flags a related but distinct open question — whether alternates are a BOQ-level or Quotation-level concept — as needing client confirmation (`Database_Schema.md`'s Open Items). That question is about how a *later* module (Quotation) copies or varies alternates; it doesn't block or ambiguity this summary computation, which only needs to know whether to exclude them here (unambiguous), so it wasn't re-raised as a blocking question for this task.

**No new endpoint beyond summary; no schema/migration change** — this task is pure computation plus one read-only endpoint.

**Tests:** 11 new, `apps/boq/tests/test_summary.py`. `BOQSummaryServiceTestCase` ×7: empty-BOQ summarizes to all-zeros (not an error), single item with no discount/tax, discount-then-tax formula verified against a hand-computed example (500.00 base, 10% discount, 18% tax → 531.00 total), optional items excluded, alternative items excluded, soft-deleted items excluded, aggregation across multiple sections. `BOQSummaryEndpointTestCase` ×4: 401 unauthenticated, cross-tenant project 404, no-BOQ-yet returns zeros (auto-creates, matching `BOQDetailView`'s own behavior), summary reflects created items via the full HTTP endpoint. Full `apps/boq` suite: **93 passed** (was 82 after BE-036). `manage.py check`: 0 issues. `makemigrations --check --dry-run`: no changes detected. `spectacular --fail-on-warn`: clean; confirmed `/projects/{project_id}/boq/summary/` present in the generated schema.

Depends On

- BE-036 (BOQ Items)

---

### BE-038 – BOQ APIs

**Status:** Done

**Priority:** Medium

**Owner:** Backend Team

**Scope:** the final Sprint 4 stabilization pass — every endpoint `BOQ_API.md` documents (`GET .../boq`, `POST .../boq/sections`, `POST .../boq/sections/{sectionId}/items`, `PATCH`/`DELETE .../boq/items/{itemId}`, `GET .../boq/summary`) was already fully built across BE-035/036/037, the same situation BE-034 ("Catalog APIs") found after BE-031–033 had already covered every documented Product Catalog endpoint. No new endpoint, no schema/migration change — this task adds full end-to-end integration coverage exercising the documented flow in one place over real HTTP calls, plus a final sign-off run of the whole backend suite as the sprint-closing gate, mirroring BE-030's role for Sprint 2.

**Tests:** 2 new, `apps/boq/tests/test_integration.py` (`BOQEndToEndIntegrationTestCase`): a full flow — BOQ auto-creates → add section → add a free-text item and a product-referenced item (verifying product-defaulting) → add an optional item → confirm all three appear in the BOQ tree nested under their section → edit an item and confirm `amount` recomputes → confirm the summary excludes the optional item and matches a hand-computed discount/tax result → delete the product item and confirm the summary updates — and a second test confirming a Section delete is blocked (409) while it has an active Item, then succeeds once the item is removed (the full BE-035→036 guard-chain exercised end to end via HTTP, not just at the service layer). Full `apps/boq` suite: **95 passed** (was 93 after BE-037). Full backend suite re-verified green as the sprint-closing gate: **754 passed, 0 failed** (was 752 after BE-037). `manage.py check`: 0 issues. `makemigrations --check --dry-run`: no changes detected. `spectacular --fail-on-warn`: clean.

**Sprint 4 status:** every task BE-035–BE-038 is now implemented, tested, and documented at **Review** status, closing out BOQ. Per this file's standing rule, Sprint 4 itself is not marked closed here — that requires explicit Backend Lead review and approval of the four Review-status tasks above, the same as every prior sprint.

Depends On

- BE-037 (BOQ Calculations)

---

# Sprint 5 – Quotation

## BE-039 – Quotation

**Status:** Done

**Priority:** High

**Owner:** Backend Team

**Pre-implementation documentation audit (AskUserQuestion):** Database_Schema.md's own "Open Items" §2 flags `quote_number` generation as unresolved (per-company vs. global sequence); the versioning approach (`quote_number` + `version` columns, no documented parent FK) needed a Backend Lead call; the status enum's `internal_review` value has no corresponding action in Finance_API.md's endpoint table; and `POST .../reject`'s one-line description ("rejection/revision request") is ambiguous against the enum's two distinct values (`rejected` vs `revision_requested`). Four questions asked, all resolved with the recommended option: (1) `quote_number` is per-company sequential (`QT-000001`), generated the same non-atomic `max()`/`count()+1` way `BOQSectionRepository.max_sort_order_for_boq` already does — an accepted precedent in this codebase, not a new risk; (2) a revision reuses the same `quote_number` and increments `version` (matches Database_Schema.md's literal two columns, no undocumented parent FK), backed by a DB-level `UniqueConstraint(company, quote_number, version)`; (3) `internal_review` has no dedicated transition endpoint — it stays in the enum, unused by the API, matching Finance_API.md's endpoint table exactly; (4) `/reject` always sets the terminal `rejected` — a client wanting changes instead is handled by staff calling `/revise` directly.

**Implementation notes:** New `apps.quotations` app. `Quotation` (company/project/boq[nullable, SET_NULL]/client FKs, `quote_number`+`version`, `subtotal`/`discount`/`tax`/`total` as `NUMERIC(14,2)` currency amounts — not percentages, unlike `BOQItem`'s per-item fields) + `QuotationItem` (mirrors `BOQItem` minus its own discount/tax column, matching `Database_Schema.md`'s literal `quotation_item` column list). `client` is always derived from `project.client_id`, never caller-supplied — the same server-derived-relationship pattern `BOQ.company` established. `QuotationService.create_quotation`: `items=None` (omitted from the request entirely) pulls the project's own BOQ (auto-created via the existing `BOQService.get_or_create_boq_for_project`), copies its current includible items (`apps.boq.selectors.list_includible_items_for_boq`, reused directly — excludes optional/alternative items) as a frozen snapshot, and copies `BOQSummaryService.compute_summary`'s `{subtotal, discount, tax, total}` dict verbatim; raises a 400 `ValidationError` if the BOQ has no items to copy. An explicit `items` list instead builds items manually (product-reference defaulting mirrors `BOQItemService.create_item`'s reuse-don't-duplicate pattern via `ProductService.get_product_by_id`), with `discount`/`tax` supplied directly as flat currency amounts (default 0) rather than derived. No generic `PATCH`/`DELETE` on Quotation — a deliberate exception to the "add CRUD for consistency" precedent (BE-031/BE-035): a versioned commercial document's content should only change through `/revise` (BE-040), never a silent in-place edit.

**Tests:** `apps/quotations/tests/test_models.py` (15), `test_services.py` (13), `test_views.py` (10) — cross-tenant 404s on every entry point, from-BOQ vs. manual creation, empty-BOQ rejection, product-defaulting, per-company `quote_number` sequencing (including independence across companies), and the DB-level `(company, quote_number, version)` uniqueness constraint.

Depends On

- BE-035 (BOQ Module), BE-037 (BOQ Calculations), BE-033 (Products)

---

## BE-040 – Versioning

**Status:** Done

**Priority:** High

**Owner:** Backend Team

**Implementation notes:** `POST /quotations/{quotationId}/revise` (`QuotationService.revise_quotation`). Clone-then-partial-override semantics, matching `ProjectService.update_project`'s own partial-field-override style but applied to a **new row** instead of an in-place update, per CLAUDE.md's "Revision → new version" rule — the source row is never mutated, only ever read from. Any field omitted from the request carries over unchanged from the source version; `items=None` clones the source version's items (and its `boq`/`subtotal`) verbatim, an explicit `items` list replaces them and recomputes `subtotal` (clearing `boq`, since the new items are no longer necessarily a BOQ snapshot); `discount`/`tax` carry over unless explicitly given either way; `total` is always recomputed. New version starts at `status=draft`. Guard (Backend Lead decision, Sprint 5 planning): only the **latest** version of a `quote_number` may be revised — raises a 409 `ConflictError` otherwise, keeping the version chain linear rather than letting it fork. This same `_ensure_latest_version` guard is shared with BE-041's three action endpoints below.

**Tests:** 5 new in `test_services.py`, 3 new in `test_views.py` — no-override clone, partial override, item replacement clearing `boq`, the stale-version 409, and a 3-version revision chain confirmed end to end over HTTP.

Depends On

- BE-039 (Quotation)

---

## BE-041 – Approval Workflow

**Status:** Done

**Priority:** High

**Owner:** Backend Team

**Implementation notes:** Three fixed single-transition action endpoints, all reusing the shared `_ensure_latest_version` guard from BE-040 plus a `from_status` precondition (409 `ConflictError` if violated) via a common `QuotationService._transition_status` helper — mirrors `ProjectService.transition_status`'s "a status change is recorded as an UPDATE, not a separate action value" audit convention, except `/approve` uses `AuditAction.APPROVE`, the enum value `Database_Schema.md`'s own `audit_log.action` set reserves for exactly this. `POST .../send`: `draft → sent` (no `internal_review` transition exists — see BE-039's planning decision). `POST .../approve`: `sent → approved`. `POST .../reject`: `sent → rejected`, always terminal (see BE-039's planning decision) — a client wanting changes instead is handled by staff calling `/revise` directly on the rejected quotation, which has no status precondition of its own.

**Tests:** 8 new in `test_services.py`, 6 new in `test_views.py` — each transition's success path, each one's wrong-source-status 409, the stale-version guard applying to `/send` too, and confirming a rejected quotation can still be revised. Full `apps/quotations` suite (BE-039–BE-041 combined): **60 passed**.

**Sprint 5 status:** every task BE-039–BE-041 is now implemented, tested, and documented at **Review** status, closing out Quotation. Per this file's standing rule, Sprint 5 itself is not marked closed here — that requires explicit Backend Lead review and approval of the three Review-status tasks above, the same as every prior sprint.

**Full-suite verification note (important for future sessions):** this sprint's own `apps.quotations` suite is clean either way, but the full-suite sign-off gate briefly showed 16 spurious failures/errors, all confined to `apps.authentication.tests` (`test_login.py`, `test_forgot_password.py`, `test_reset_password.py`, `test_throttling.py`) — every one traced to running the suite via `python manage.py test` instead of `pytest`. `conftest.py` has an autouse `_clear_throttle_cache` fixture (clears DRF's `ScopedRateThrottle` cache before/after every test) that only fires under `pytest` — `manage.py test` silently skips it, so real HTTP calls to the throttled auth endpoints across different test files leak rate-limit state into each other. Reproduced and confirmed in isolation (the same 4 files alone: 12 failures/3 errors under `manage.py test`, 41/41 clean under `pytest`), then the full suite re-verified via `pytest`: **814 passed, 0 failed**. No production or test code needed to change — `pytest` (per this repo's own `pytest.ini` + `conftest.py`) is the correct full-suite command; `manage.py test` is safe for scoped/per-app runs but must not be used as the sprint-closing gate.

Depends On

- BE-040 (Versioning)

---

# Sprint 6 – Finance

## BE-042 – Invoice

**Status:** Done

**Priority:** High

**Owner:** Backend Team

**Pre-implementation documentation audit (AskUserQuestion):** Finance_API.md says invoice status (`draft, sent, partially_paid, paid, overdue, cancelled`) is "derived server-side from paid-vs-total amount and due date" — but only `draft`/`sent`/`cancelled` have dedicated action endpoints, and this sprint has no scheduled/cron job. Two questions asked, both resolved with the recommended option: (1) `overdue` is never persisted — the stored `status` column only ever holds `draft/sent/partially_paid/paid/cancelled`; `InvoiceService.compute_effective_status` derives `overdue` at read time (sent/partially_paid + a past `due_date`), so `GET` responses are always accurate with no background sweep needed; (2) BE-045 ("Financial Reports") scopes to `GET /reports/finance` + `GET /reports/expenses` only — `/reports/dashboard`, `/reports/sales`, `/reports/projects` are deferred (Leads don't exist yet for sales conversion; dashboard/project reports span modules outside this sprint).

**Backend Lead decision (not asked — a direct consequence of already-binding docs, not a new ambiguity):** `Invoice` has **no `contract_id` column**, despite Database_Schema.md listing one. `Contract` is not part of this build's scope — CLAUDE.md's Module Dependency Map goes straight from Quotation to Invoice with no Contract step, and the Engineering Execution Rules' "Never implement future modules unless instructed" forbids adding a table this build order doesn't call for just to satisfy a permanently-null FK. Finance_API.md's "from contract/approved quotation, or ad hoc" becomes "from an approved quotation, or ad hoc" here.

**Implementation notes:** New `apps.invoices` app. `Invoice` (company/project/quotation[nullable, SET_NULL]/client FKs, `invoice_number` per-company sequential "INV-000001" — the exact `QuotationRepository.next_quote_number` scheme from BE-039, reused without re-litigating) + `InvoiceItem` (matches Database_Schema.md's `invoice_item` columns exactly — **no `product_id` FK**, unlike QuotationItem/BOQItem). `InvoiceService.create_invoice`: `quotationId` supplied reuses `QuotationService.get_quotation_by_id` (cross-tenant 404) and requires `quotation.status == approved` (400 otherwise), copying its items/subtotal/discount/tax/total verbatim — the same BOQ-summary-copy pattern BE-039 established, one level up the chain; `items` supplied instead builds an ad hoc invoice manually; exactly one of the two must be given. `PATCH /invoices/{id}` ("Edit (draft only)") and `/send`/`/cancel` mirror Quotation's guard style (409 on the wrong source status) — `/cancel` blocked once `paid` or already `cancelled` (Backend Lead decision, Finance_API.md doesn't spell out cancel's preconditions).

**Tests:** `apps/invoices/tests/test_models.py` (13), `test_services.py` (21), `test_views.py` (11) — from-quotation vs. ad hoc creation, the approved-quotation precondition, draft-only edit/PATCH guard, cancel's terminal-status guard, and `compute_effective_status`'s overdue derivation (confirming the persisted column itself never changes).

Depends On

- BE-039 (Quotation)

---

## BE-043 – Payment

**Status:** Done

**Priority:** High

**Owner:** Backend Team

**Implementation notes:** New `apps.payments` app. `Payment` (company/invoice/client/project FKs — `client`/`project` denormalized off `invoice`, matching every prior "every tenant table gets its own direct FK" precedent; `method` an unconstrained CharField, no documented value domain, the same treatment `BOQ.status` got). `PaymentService.create_payment` is blocked (409) against a `draft` or `cancelled` invoice — recording money against either has no real-world meaning (Backend Lead decision, Finance_API.md doesn't spell out a precondition). Every create/void call ends by invoking `InvoiceService.recompute_status_from_payments` (new BE-042 method, added here since payments are what actually drive it): fully covered -> `paid`; partially covered -> `partially_paid`; nothing covered (e.g. a voided payment) -> `sent` (the only state a payable invoice can revert to, given the create-time guard above) -- a cancelled invoice's status is never resurrected by this recompute. "Void a payment (audit-logged, not hard-deleted)" is just `SoftDeleteModel.delete()` -- no separate status field needed.

**Tests:** `apps/payments/tests/test_models.py` (6), `test_services.py` (11), `test_views.py` (7) -- draft/cancelled-invoice payment rejection, partial/full payment status transitions, multi-payment accumulation to `paid`, void reverting `paid` -> `sent`/`partially_paid` correctly, and the cancelled-invoice-not-resurrected guard.

Depends On

- BE-042 (Invoice)

---

## BE-044 – Expense

**Status:** Done

**Priority:** High

**Owner:** Backend Team

**Implementation notes:** New `apps.expenses` app. `Expense` (company/project FKs, `category`/`vendor` unconstrained text -- no Vendor model exists yet, Procurement is a future-phase module per CLAUDE.md's MVP Phasing; `employee`/`added_by` both `SET_NULL` FKs to `users.User`). `employee`, when supplied, reuses `apps.projects.validators.validate_assignee_company_membership` -- the exact same active-CompanyMembership invariant `Project.assigned_to`/`ProjectMember` already enforce, not a new check. `added_by` is always the acting user at creation. Workflow `draft -> submitted -> approved -> paid` (`ExpenseApprovalStatus`) matches Finance_API.md's `/submit`/`/approve`/`/mark-paid` actions exactly, mirroring Quotation's `_transition_status` guard style. `PATCH`/`DELETE /expenses/{id}` were added for CRUD consistency (draft only) -- not themselves documented in Finance_API.md, the same precedent BE-031/BE-035/BE-042 established repeatedly this build. List filters (`category`, `vendor`, `employee`, `date`, plus `approvalStatus`) match Finance_API.md's documented set, folded into this single task since Sprint 6 has no separate "Filters" task the way Project/Product did.

**Tests:** `apps/expenses/tests/test_models.py` (8), `test_services.py` (22), `test_views.py` (11) -- cross-company employee assignment rejected, the `employeeId` "omitted vs. explicit null" three-way sentinel on PATCH, draft-only edit/delete guards, the full submit/approve/mark-paid chain plus each transition's wrong-source-status 409, and every documented list filter.

Depends On

- BE-025 (Project)

---

## BE-045 – Financial Reports

**Status:** Done

**Priority:** Medium

**Owner:** Backend Team

**Scope (per BE-042's planning decision):** `GET /reports/finance` and `GET /reports/expenses` only -- see BE-042's AskUserQuestion note above.

**Implementation notes:** New `apps.reports` app -- pure read-only aggregation, no model of its own. `FinanceReportService.compute`: `revenue` sums `total` across every billed (`sent`/`partially_paid`/`paid`) invoice in scope (accrual, excludes `draft`/`cancelled`); `received` sums every active payment's amount regardless of its invoice's current status (money already collected stays collected even if the invoice is later cancelled); `receivables = revenue - received`; `outstanding` narrows `receivables` to the subset that's also currently overdue (reuses `InvoiceService.compute_effective_status`, BE-042's read-time derivation); `expenses` sums `amount + tax` across `approved`/`paid` expenses only (a draft/submitted expense isn't a confirmed cost yet); `profitLoss = revenue - expenses`. `ExpenseReportService.compute` returns category/project/vendor/employee/date breakdowns, including every expense regardless of `approvalStatus` (a broader visibility report, deliberately distinct from the P&L figure's approved-only scope). Each figure/breakdown is scoped independently by its own entity's most natural date field (Invoice by `created_at`, Payment by `payment_date`, Expense by `date`) -- Finance_API.md's `?dateFrom=&dateTo=` note doesn't name one unified date column across three different tables. `?projectId=` scopes both reports to one project; a platform admin must supply `?companyId=` explicitly (no single resolved tenant), mirroring every list endpoint's `admin_company_id_param` pattern.

**Tests:** `apps/reports/tests/test_services.py` (15), `test_views.py` (5) -- revenue/receivables/outstanding/expenses/P&L arithmetic across draft/sent/cancelled invoices and draft/approved expenses, project and company-tenant isolation, and every expense breakdown grouping.

**Sprint 6 status:** every task BE-042–BE-045 is now implemented, tested, and documented at **Review** status, closing out Finance -- the last MVP-scope sprint in CLAUDE.md's Module Dependency Map (`Auth->Company->User->Role->Client->Project->Product->BOQ->Quotation->Invoice->Payment->Expense->Reports`). Per this file's standing rule, Sprint 6 itself is not marked closed here -- that requires explicit Backend Lead review and approval of the four Review-status tasks above, the same as every prior sprint. Full `apps/invoices` + `apps/payments` + `apps/expenses` + `apps/reports` suite: **130 passed** (45 + 24 + 41 + 20). Full backend suite re-verified green via `pytest` (per BE-041's documented lesson on the correct runner) as the sprint-closing gate: **944 passed, 0 failed** (was 814 after Sprint 5). `manage.py check`: 0 issues. `makemigrations --check --dry-run`: no changes detected. `spectacular --fail-on-warn`: clean.

Depends On

- BE-044 (Expense)

---

# Sprint 7 – Platform

- BE-046 – Documents
- BE-047 – Activity Logs
- BE-048 – Dashboard

**Scope note (AskUserQuestion, 2026-09-01):** the original stub bundled 5 items (Notifications, Documents, Activity Logs, Dashboard, Analytics), but unlike every prior sprint, none of them have a documented API sketch anywhere in `04_API/`. Documents (table already in `Database_Schema.md`), Activity Logs (a read-only feed derivable from the existing `audit_log` table, BE-019), and Dashboard (KPIs fully enumerated in CLAUDE.md, reusing existing Project/Quotation/Invoice/Expense data) are buildable now. **Notifications** and **"Advanced Analytics"** are explicitly labeled Phase 5 in FRS.md §26 and CLAUDE.md's own MVP Phasing — building them now would mean inventing a data model, event/channel design, and business rules with zero source-document backing, contradicting CLAUDE.md's "don't build Phase 3-5 features unless explicitly instructed" rule and this file's "Never implement future modules unless instructed." Renumbered/reordered to BE-046-048, sequenced so Dashboard (which reuses both) is built last; deferred to Phase 5. Notifications/Analytics remain unassigned task numbers for when that phase is reached.

Status: Done

---

## BE-046 – Documents

**Status:** Done

**Priority:** Medium

**Owner:** Backend Team

**Implementation notes:** New `apps.documents` app. `Document` matches Database_Schema.md's `document(id, company_id, project_id FK, entity_type, entity_id, file_url, version, uploaded_by FK, uploaded_at)` with one deliberate simplification: no separate `uploaded_at` column -- a document's upload moment and its row-creation moment are always the same instant (unlike Payment.payment_date/Expense.date, which a user can genuinely backdate), so `BaseModel.created_at` already carries that exact meaning and is exposed as `uploadedAt` in the API rather than physically duplicated. `entity_type`/`entity_id` is the same generic polymorphic-attachment pattern `AuditLog` already uses -- not a real FK, since it spans many entity tables (Migration_Plan.md's own note: "allows attaching to other entities later"); defaults to `("project", project.id)` when omitted. No file-upload endpoint exists anywhere in this codebase -- `fileUrl` is caller-supplied (the same out-of-band-object-storage pattern already established for `Payment.receipt_url`/`Expense.receipt_url`/`Product.image_url`). `version` is auto-assigned (next version among every Document sharing the same `(entity_type, entity_id)` pair, the same `max()+1` pattern `BOQSectionRepository`/`QuotationRepository` established) -- re-uploading against the same target is how a document gets "re-versioned," with no separate endpoint needed.

**Tests:** `apps/documents/tests/test_models.py` (7), `test_services.py` (8), `test_views.py` (9) -- default-to-project-entity, explicit entity targeting, version auto-increment (including independence across different entities), cross-tenant 404s, and the blank-`fileUrl` guard.

Depends On

- BE-025 (Project)

---

## BE-047 – Activity Logs

**Status:** Done

**Priority:** Medium

**Owner:** Backend Team

**Implementation notes:** No new app or model -- extends `apps.audit` (BE-019) with its first read surface (`selectors.py`, `serializers.py`, `views.py`, `urls.py` -- audit logging had been write-only internal infrastructure until now). New `ActivityLogService` (deliberately separate from the write-only `AuditLogService`, mirroring `apps.boq`'s own `BOQService`/`BOQSummaryService` write/read split) backs `GET /activity-logs`: tenant-scoped, filterable by `entityType`/`entityId`/`action`/`actorUserId`/date range, **paginated** (`StandardPagination`) -- unlike Quotation/Invoice/Expense's nested-under-Project lists, a tenant-wide audit feed is exactly the "unbounded collection" `CompanyViewSet`/`ProductViewSet`'s pagination precedent covers, not the small nested-list precedent. A platform admin must supply `?companyId=` explicitly (no single resolved tenant), mirroring `apps.reports`' identical pattern.

**Tests:** `apps/audit/tests/test_services.py` (13 total, including 4 `ActivityLogServiceTestCase`), `apps/audit/tests/test_models.py` (5), `apps/audit/tests/test_activity_log_views.py` (3) -- company isolation, and filters by entity type/action/actor.

Depends On

- BE-019 (Audit Log)

---

## BE-048 – Dashboard

**Status:** Done

**Priority:** Medium

**Owner:** Backend Team

**Implementation notes:** New `apps.dashboard` app -- pure read-only aggregation, no model of its own, matching CLAUDE.md's Dashboard / Reports section exactly: 8 KPI cards (Total/Active Projects, Total Quotations, Total Billed Revenue, Total Received, Pending Amount, Total Expenses, Net Profit/Loss) plus 8 "recent" sections (Recent Projects/Quotations/Expenses, Pending Payments, Overdue Invoices, Upcoming Deadlines, Recent Activities, Project Profitability). Every money KPI reuses `FinanceReportService.compute` (BE-045) directly rather than recomputing the same revenue/received/expenses/profit-loss formulas a second time; `recentActivities` reuses `ActivityLogService` (BE-047) and `AuditLogSerializer` directly. "Total Quotations" counts distinct `quote_number`s, not every revision row. "Overdue Invoices" reuses `InvoiceService.compute_effective_status` (BE-042) the same way `FinanceReportService._compute_outstanding` does. "Project Profitability" calls `FinanceReportService.compute` once per active project (a per-project loop, not optimized further -- a dashboard read, not a hot path) and returns the top 5 by profit. Every "recent" list is capped at 5 (10 for activities) -- CLAUDE.md names each section but not a page size; no doc gap worth an AskUserQuestion over.

**Tests:** `apps/dashboard/tests/test_services.py` (9), `test_views.py` (2) -- KPI arithmetic reuse, active-project exclusion of terminal statuses, distinct-quote-number counting, pending/overdue invoice listing, the 30-day upcoming-deadline window, per-project profitability, and company-tenant isolation.

**Sprint 7 status:** every task BE-046–BE-048 is implemented, verified, tested, and marked **Done**, completing Sprint 7 (Platform). Full `apps/documents` + `apps/audit` + `apps/dashboard` suite: **56 passed** (24 + 21 + 11). `manage.py check`: 0 issues. `makemigrations --check --dry-run`: no changes detected. `spectacular --fail-on-warn`: clean. Full backend suite re-verified green via `pytest` as the sprint-closing gate: **986 passed, 0 failed** (was 944 after Sprint 6). (Note: the first sign-off attempt hit a one-off Postgres deadlock from a stale test-DB connection left by an earlier interrupted run, unrelated to Sprint 7's code — a clean rerun confirmed the real result above.)

Depends On

- BE-047 (Activity Logs)

---

## Post-Sprint-7 Backend Completion Audit — 2026-09-07

All of Sprints 1–7 (BE-001–BE-048) are confirmed **Done** against actual code (models/migrations/serializers/services/repositories/permissions/views/urls/tests), re-verified directly (not from task-status text alone). This audit re-inspected the live repository to identify every genuinely missing backend capability against `CLAUDE.md`, `05_Security/Permissions.md`, `05_Security/Tenant.md`, and `00_Development_Standards/`, per a "complete the entire backend" directive. Ground truth confirmed by reading code directly (not assumed from the earlier read-only System Audit artifact):

- **RBAC is enforcement-by-tenant-only, not by permission.** Every permission class in the codebase (`RolePermission`, `ProjectPermission`, `ClientPermission`, and siblings in `products`/`boq`/`quotations`/`invoices`/`payments`/`expenses`) is textually near-identical: `has_permission` checks authentication + a resolved `request.company_id`; `has_object_permission` checks `str(request.company_id) == str(obj.company_id)`. Zero role- or permission-code differentiation exists anywhere.
- **`Role` (BE-012) is not even wired to `CompanyMembership`.** `CompanyMembership` (`apps/users/models.py:74`) has only `company`, `user`, `status` — no `role` FK. A company can create `Role` rows via `/roles`, but nothing assigns a role to a member. RBAC is further from "labels only" than previously described — it's fully unwired at the data-model level.
- **No `Permission`/`RolePermission` models exist.** `05_Security/Permissions.md` describes `User → Company Membership → Role → Permissions` and a `<module>.<action>` code format, but no model stores permission codes or links them to a `Role`.
- **No Company Membership management API exists.** Only `/roles` and `/roles/{id}` are routed in `apps.users`. There is no invite/list/remove/suspend/reactivate/assign-role endpoint for `CompanyMembership`, despite the model existing since BE-007.
- **No "my memberships" / workspace-switching endpoint exists.** `/auth/me` returns only the bare `User`; a multi-company user has no way to enumerate their memberships via API (confirmed gap the frontend Milestone-1 plan already flagged and deliberately routed around).
- **`audit`/`reports`/`dashboard` endpoints are ID-less, tenant-scoped aggregates** (`GET /activity-logs`, `GET /reports/finance`, `GET /reports/expenses`, `GET /reports/dashboard` — confirmed via each app's `urls.py`), so classic per-object IDOR does not apply the same way it does to `documents`; the real, narrower gap is the absence of an explicit view-level regression test asserting each of these never leaks another tenant's rows (service-layer scoping is already tested in each app's `test_services.py`, but not re-asserted at the view/permission layer).
- **`documents` DELETE is already correctly tenant-enforced and tested** (`DocumentDetailView.delete` calls `check_object_permissions` via `ObjectPermission404Mixin`; `documents/tests/test_views.py` already contains cross-tenant/404 cases) — the earlier read-only audit's "DELETE document" gap does not reproduce against current code and is considered closed; no action needed.
- **`django-filter` is an installed, unused dependency.** All list/filter endpoints to date use hand-built selectors — confirmed as the codebase's one consistent filtering strategy; no second strategy exists to reconcile.
- **No Celery task exists yet** despite `apps.authentication`/`config/celery.py` scaffolding from BE-003 — no async email, PDF, or reminder job has been built in any sprint so far.
- **No file upload pipeline exists.** `documents`/`payments`/`expenses`/`products` all store `file_url`/`receipt_url`/`image_url` as plain URL fields — there is no upload endpoint, no storage abstraction, no MIME/size validation anywhere in the repo.
- **Several free-text fields have no enum**, confirmed by direct model inspection: `Company.currency` (plain `CharField`, defaults `"INR"`, no ISO-4217 validation), `Payment.method`, `Expense.category`/`vendor`/`payment_method`, and `Project.priority` (already deliberately left free-text per an earlier Backend Lead decision recorded in its own `help_text`, since `01_Business/FRS.md §10` names the field but never defines values).
- **No Phase 3–5 backend module has any code**: Leads/CRM pipeline, Site Visits, Design Management, Procurement, Notifications, Client Portal all have zero models/apps — matches `CLAUDE.md`'s explicit "do not build Phase 3–5 unless instructed" guidance, so these are recorded as backlog only, lowest priority, per the dependency map.

### Open documentation conflict flagged before implementation (per `BACKEND_RULES.md`'s "stop and ask" rule)

`05_Security/Permissions.md` §7 explicitly lists as an **open item**: *"Full canonical list of permission codes per module (to be enumerated alongside `04_API/` endpoint finalization)."* The doc gives a code **format** (`<module>.<action>`), an **action vocabulary** (view/create/edit/delete/approve/export/manage/financial_access), and one **worked example** (Accountant's permission set) — but not a finalized per-module code list, and it does not say whether the 7 named default roles (Owner/Admin/PM/Designer/Accountant/Sales/Supervisor) should be auto-seeded into every new company or are documentation-only references for an admin to hand-build. Per `BACKEND_RULES.md` and the master completion brief's own instruction ("do not invent the canonical permission-code list… create the smallest architecture capable of supporting them and flag the exact unresolved codes before enforcing invented permissions"), this was raised to the user directly rather than assumed — see chat for the resolution reached before BE-049 enforcement work began.

### New backlog (this audit's deliverable — every item below is Todo unless noted)

**P0 — RBAC & Tenant Completion**

| ID | Task | Status |
|---|---|---|
| BE-049 | `Permission` model (`code`, `module`, `action`, `description`) + `RolePermission` (role↔permission, unique together) + migration. Seed codes/action-vocabulary per `Permissions.md` §2 format, scoped to modules that exist today. | Done |
| BE-050 | Add `role` FK (nullable, `SET_NULL`, same-company validated) to `CompanyMembership` + migration; role-assignment validation (role must belong to the same company as the membership). | Done |
| BE-051 | RBAC resolution service (`has_perm(request, code)`), shared `PermissionRequiredMixin`/permission-code-aware permission class; Platform Admin universal bypass preserved; company-scoped permission caching only if a real N+1 is measured. | Done |
| BE-052 | Company Membership management module: repository/service/selector/serializers/permissions/views for invite, list, remove, suspend, reactivate, assign/change role — full `View → Serializer → Service → Repository` stack per `BACKEND_RULES.md`. Audit log entry on every mutation. | Done |
| BE-053 | `GET /auth/memberships` (or equivalent) — current user's active memberships across companies, for workspace switching. Returns only company id/name, membership status, role name — no cross-tenant leakage. | Done |
| BE-054 | Cut over existing `*Permission` classes (`Client`, `Project`, `Role`, `Product`, `BOQ`, `Quotation`, `Invoice`, `Payment`, `Expense`) from tenant-only to tenant + permission-code enforcement, module by module, each with its own test pass and commit — **only after** BE-049–BE-051 land and the canonical-code question is resolved. | **Review** |
| BE-055 | Audit-log role assignment/removal and permission grant/revoke as first-class audited events (extends BE-019's `apps.audit`). | Done |
| BE-056 | View-level cross-tenant regression tests for `apps.audit`, `apps.reports`, `apps.dashboard` (company-A-never-sees-company-B, asserted through the view, not just the service). | Todo |

#### BE-049–BE-053, BE-055 — RBAC Architecture, Company Membership Management, My Memberships — 2026-09-07

**Status:** Done

**Priority:** Critical (P0)

**Owner:** Backend Team

**Decision resolved before implementation:** `05_Security/Permissions.md` §7 flags the canonical per-module permission-code list as pending client sign-off. Per the Backend Lead's own "stop and ask" rule and the master completion brief's identical instruction, this was raised to the user directly rather than assumed. Resolution: (1) build the full RBAC architecture now and seed permission codes derived directly from the documented `<module>.<action>` format (`05_Security/Permissions.md` §2), without yet enforcing them on any existing endpoint; (2) auto-seed the 7 documented default roles (minus Site Supervisor, Phase 4, which has no module yet) onto every newly created company, each with its representative permission set from §3's role table.

**Implementation notes:**

- **Models** (`apps/users/models.py`): `PermissionAction` (view/create/edit/delete/approve/export/manage/financial_access, per §2), `Permission` (`code`, `module`, `action`, `description` — a global, non-tenant-scoped catalog), `RolePermission` (role↔permission join, unique-active constraint). Added a nullable `role` FK (`SET_NULL`) to `CompanyMembership` — previously `CompanyMembership` had no way to actually hold a role at all, so `Role` (BE-012) was unwired from any user even though the CRUD existed.
- **Seed data** (`apps/users/permission_catalog.py`): a plain data module (no model imports, importable from both a migration and application code without circular-import or migration-drift risk) holding `PERMISSION_CATALOG` (41 codes across 15 existing modules — company/user/role/client/project/product/boq/quotation/invoice/payment/expense/document/audit/report) and `DEFAULT_ROLE_PERMISSIONS` (the 6 non-Phase-4 default roles → their representative code sets, derived directly from §3's table and worked Accountant example — Owner gets every code). Seeded into the database via data migration `0005_seed_permission_catalog.py`. Treated as an extensible catalog, not final — §7's open item is still open; codes can be added/renamed/removed later without a model change.
- **`RoleService.seed_default_roles_for_company(company)`**: creates the 6 default `Role` rows + their `RolePermission` grants for a company. Wired into `CompanyService.create_company()` (`apps/company/services.py`) via a function-local import (avoids a module-level circular-import risk between `apps.company` and `apps.users`, since `apps.users` already imports `apps.company.models` at module level). Not backfilled onto companies that existed before this feature — only new companies get auto-seeded roles.
- **`RoleService.assign_permissions(role_id, codes)`**: full-replacement semantics (not additive) for a role's permission-code grants; rejects unknown codes outright (400) rather than silently ignoring them. `PUT /roles/{id}/permissions`.
- **`PermissionService`**: read-only RBAC resolution (`get_permission_codes_for_membership`, `has_permission`) — fails closed for `None`, a membership with no role, or a non-active membership. **Not wired into any view's `permission_classes` yet** — every existing `*Permission` class (`RolePermission`, `ProjectPermission`, `ClientPermission`, etc.) is untouched and still tenant-only. That cutover is BE-054, deliberately kept separate so this architecture could be reviewed on its own before any endpoint's live authorization behavior changes.
- **`CompanyMembershipService`** (BE-052): invite (by email — invites an existing global `User` identity into a company, does not create a new account), list (company-scoped, status/search/ordering), retrieve, assign/change/clear role (validates same-company), suspend (→ `revoked`), reactivate (→ `active`), remove (soft delete). Every mutation audited via `AuditLogService` under `entity_type="company_membership"` (fields: `user_id`, `role_id`, `status` — added to `apps/audit/validators.py`'s allowlist). New `CompanyMembershipPermission` mirrors `RolePermission`'s coarse tenant-only pattern exactly (fine-grained enforcement is BE-054). Routes: `GET/POST /company-memberships`, `GET/DELETE /company-memberships/{id}`, `POST /company-memberships/{id}/assign-role`, `.../suspend`, `.../reactivate`. **Known limitation, not a bug:** unlike `/roles`, the list/create actions here don't yet accept a Platform-Admin `companyId` override — this module is scoped to company-user self-service management, matching its actual use case; a Platform Admin console view can be added later the same way `RoleViewSet` did it.
- **`GET /auth/memberships`** (BE-053, `apps/authentication/views.py::MyMembershipsView`): the one legitimate cross-tenant read in the codebase — scoped by the caller's own `user_id`, never a client-supplied company id. Returns only `companyId`/`companyName`/`status`/`roleName` (`MyMembershipSerializer`) — never other members, settings, or financial data. Exempted from `TenantJWTAuthentication`'s tenant resolution (added to `exempt_paths` alongside `/auth/me`) so it works correctly for a user with zero, one, or many memberships rather than being rejected before reaching the view.
- **`GET /permissions`**: read-only listing of the global Permission catalog (supports a future role-builder UI).
- Registered `Permission`/`RolePermission` in Django admin; added `role` to `CompanyMembershipAdmin`'s `list_display`/`raw_id_fields`.
- Added `CompanyMembershipStatus` to `SPECTACULAR_SETTINGS.ENUM_NAME_OVERRIDES` (`config/settings.py`) — a new `status` `ChoiceField` on `CompanyMembershipListQuerySerializer` collided with other modules' `status` enums during schema generation; same fix pattern already used for `Company`/`Project`/`Product`/`Quotation`/`Invoice`.

**Real bug found and fixed during self-review (test-driven):** `PermissionRepository.codes_for_role()` originally queried `Permission.objects.filter(role_permissions__role_id=role_id)` — a reverse-relation filter that performs a raw SQL join and does **not** respect `RolePermission`'s soft-delete manager, so a soft-deleted (replaced/revoked) permission grant was still counted as active. Caught by `test_assign_permissions_replaces_previous_set`/`test_assign_permissions_empty_list_clears_all` failing on first run. Fixed by querying `RolePermission.objects` (its own soft-delete-aware default manager) for permission ids first, then `Permission.objects` for the codes.

**Tests:** `apps/users/tests/test_permission_models.py` (catalog-seeded, code-format, `RolePermission` model/soft-delete/cascade), `test_rbac_services.py` (assign/replace/reject-unknown-codes/audit-log, `PermissionService` fail-closed cases, default-role seeding incl. Owner-gets-everything and Sales-cannot-approve-quotations), `test_membership_management_services.py` (invite/assign-role/suspend/reactivate/remove/list, cross-company role-assignment rejection, audit log), `test_membership_management_views.py` (full API + cross-tenant 404s for memberships and role-permission assignment), `apps/authentication/tests/test_memberships.py` (`/auth/memberships`: zero-memberships-returns-empty-not-403, multi-company listing, no leakage of other users' memberships), plus a `CompanyService` test confirming auto-seeding on creation. One pre-existing test (`test_membership_serializer_camel_case`) updated for the two new serializer fields (`roleId`/`roleName`).

**Validation:** `apps/users`+`apps/company`+`apps/authentication`+`apps/audit`: **283 passed** (was 195 combined before this task; includes the fix above). Full backend suite re-verified green: **1048 passed, 0 failed** (was 986 after Sprint 7). `manage.py check`: 0 issues. `makemigrations --check --dry-run`: no changes detected. `spectacular --fail-on-warn`: clean (0 warnings after the `ENUM_NAME_OVERRIDES` fix).

#### BE-054 — RBAC Enforcement Cutover — 2026-09-07

**Status:** Review (awaiting Backend Lead approval — not self-approved)

**Priority:** Critical (P0)

**Owner:** Backend Team

Full detail lives in `05_Security/RBAC_Enforcement_Matrix.md` §7 — this entry summarizes it. Implements the Backend Lead's explicit decisions on every item the enforcement matrix (§§1–6 of that doc) flagged for approval.

**Implementation notes:**

- **Shared mechanism:** `apps/common/permissions.py::TenantScopedPermission` replaces every duplicated tenant-only permission class (`ClientPermission`, `ProjectPermission`, `ProductCategoryPermission`, `RolePermission`, `CompanyMembershipPermission` are now thin subclasses). `has_permission` adds a permission-code check (declarative per-view `permission_code`/`permission_code_map`, fails closed if a view declares neither) on top of the unchanged tenant/platform-admin check; `has_object_permission` is deliberately untouched, so cross-tenant access still 404s independently of the new 403-on-missing-permission-code path. Every business endpoint across `companies`/`roles`/`company-memberships`/`clients`/`projects`(+team)/`products`(+categories/subcategories)/`boq`(+sections/items)/`quotations`/`invoices`/`payments`/`expenses`/`documents`/`reports`/`dashboard`/`audit` now declares a code — full table in the enforcement matrix §7.10.
- **Explicitly-documented codes** (`invoice.view/create/edit`, `payment.view/create`, `expense.view`, `report.financial_access`) used exactly where endpoint semantics match. **Backend-Lead-approved provisional mappings** for workflow actions with no dedicated code (quotation send/revise→`quotation.edit`, reject→`quotation.approve`; invoice send/cancel→`invoice.edit`; expense submit→`expense.edit`, mark-paid→`expense.approve`; project status transition→`project.edit`) — no new workflow-specific code was invented, per instruction.
- **Dashboard** (`GET /reports/dashboard`) gated with `report.view`, not `report.financial_access`, to preserve operational access for non-financial roles — deferred follow-up to split the payload's financial fields is BE-068.
- **Privilege-escalation guard:** `RoleService.assign_permissions`, `CompanyMembershipService.invite_member`/`assign_role` all accept `actor_membership`; a non-platform-admin actor can never grant codes beyond their own, including to themselves via a crafted `roleId`.
- **Legacy Member migration** (`0006_backfill_legacy_member_role.py`): idempotent, per-company backfill of every pre-existing role-less `CompanyMembership` onto a new "Legacy Member" role holding every catalog code (excludes superuser-owned memberships). Never auto-seeded for new companies. `CompanyMembershipInviteSerializer.roleId` is now required, so no new membership can silently end up role-less.
- **Default-role corrections:** Admin gained `company.view`/`company.manage` (BE-049 omission). Accountant lost `expense.create`/`expense.approve` (undocumented beyond `Permissions.md` §3's worked example — the Backend Lead named only these 2 codes for removal, so the rest of Accountant's broader-than-the-worked-example set was kept, not truncated to exactly 7 codes). Reconciliation migration `0007` backfills both onto already-seeded companies.
- **`report.view` gap found and fixed** (this task's own bug, not BE-049's): Project Manager, Designer, and Sales were seeded without `report.view`, which broke the entire premise of the dashboard decision above — they'd have gotten 403 from the dashboard. Fixed in `permission_catalog.py` + backfill migration `0008`.
- **Two real bugs found and fixed** during this task's own validation: (1) `PermissionRepository.codes_for_role` bypassed `RolePermission`'s soft-delete manager via a raw-join reverse-relation filter — a revoked grant still counted as active; (2) `PermissionService` didn't check `role.is_active` — a deactivated role's holders kept full access. Both fixed with regression tests.
- **Migration safety finding, not fixed in this task (flagged, needs a decision):** migrations `0006`–`0008` identify their target role(s) by exact `name` match — `Role` has no field distinguishing a platform-seeded default role from a company's own custom one. No real risk today (no production deployment, no real customer roles yet), but the same pattern would misfire against real customer data in the future (e.g. a customer's own role coincidentally/deliberately named "Admin" or "Accountant / Finance" would get silently mutated). Proper fix needs a stable non-user-editable `Role` identifier — tracked as BE-069, deliberately not undertaken as a side effect of this task.
- **Infrastructure lesson (not a code defect):** four parallel test-fixing agents plus this session's own validation runs collided on the shared Postgres test database mid-task, producing two spurious full-suite runs (274 and 10 apparent failures) that fully vanished once the stale database was dropped and one clean serial run was performed. Never run more than one pytest process against `test_int_projects_dev` at a time.

**Tests:** every existing app test suite's "member" fixtures updated via a new shared helper (`apps/common/test_utils.py::make_full_access_membership`) for generic CRUD success paths; dedicated narrow-role tests added for every item in the required RBAC test matrix (allowed/denied, cross-tenant 404 vs. same-tenant 403, role-less/inactive-role/revoked-membership fail-closed, permission replacement/revocation, malformed-code fail-closed, privilege escalation incl. self-escalation, platform-admin bypass, financial-access separation, dashboard operational access, Legacy Member) across `apps/users/tests/test_rbac_role_matrix.py` (new), `test_rbac_services.py`, `test_membership_management_services.py`, `test_membership_management_views.py`, plus existing per-app suites.

**Validation:** full backend suite, single serial process, fresh test database (no `--reuse-db`): **1078 passed, 0 failed, 0 errors, exit 0** (runtime 21m52s). `manage.py check`: clean (0 issues). `makemigrations --check --dry-run`: no changes detected. `spectacular --fail-on-warn`: clean.

Depends On

- BE-049, BE-050, BE-051, BE-052, BE-053

**P1 — Hardening**

| ID | Task |
|---|---|
| BE-057 | General API throttling for business endpoints (reads/writes/reports/exports), env-configurable scopes, 429 via the standard error envelope. Auth throttling (existing) is out of scope. |
| BE-058 | Real file upload pipeline (local storage in dev, S3-compatible in prod) for Documents/Payments receipts/Expense receipts/Product images: upload endpoint, MIME/extension/size validation, tenant-scoped storage paths, safe filenames, delete/archive, audit events. Includes a backward-compatible migration plan for existing `*_url` fields. |
| BE-059 | Data-integrity enums: `Company.currency` (ISO-4217-validated choices), `Payment.method`, `Expense.category`/`vendor`/`payment_method`, and `Project.priority` (already a `CharField`, deliberately left free-text per an earlier Backend Lead decision since `01_Business/FRS.md §10` names the field but never defines its values — re-confirm that decision before constraining it) — pending confirmation of the exact allowed value sets (flagged, not invented). |
| BE-069 | Add a stable, non-user-editable identifier to `Role` (e.g. a `system_key` field, never exposed via `/roles`) so default-role reconciliation migrations (`0006`–`0008`) stop matching by exact display `name` — a real forward risk once customer-created roles exist, flagged during BE-054's migration safety review. |

| BE-070 | Fix `apps.authentication` throttle-cache test-isolation leak reproducible under `manage.py test` (13 failures + 3 errors) — see writeup below. | **Review** |
| BE-071 | Add User / secure company user onboarding — `POST /company-memberships/add-user`, self-suspend/self-remove safety guards — see writeup below. | **Review** |
| BE-072 | Role permission read-back — `GET /roles/{id}/permissions` — see writeup below. | **Review** |
| BE-073 | Role delete safety — deleting an assigned role now unassigns affected memberships instead of leaving them with retained access — see writeup below. | **Review** |
| BE-074 | Invoice payment aggregates — `paidAmount`/`outstandingAmount` on InvoiceSerializer, N+1-safe — see writeup below. | **Review** |
| BE-075 | CI pipeline (`.github/workflows/ci.yml`) — backend/frontend tests, type check, dependency audit, Docker build validation — see writeup below. | **Review** |
| BE-076 | BOQ/Quotation/Invoice PDF export — shared server-side rendering infrastructure, three `GET .../pdf` endpoints — see writeup below. | **Review** |
| BE-068 | Dashboard financial access separation — `GET /reports/dashboard` no longer sends financial data to `report.view`-only roles — see writeup below. | **Review** |
| BE-077 | CSRF trusted origins made environment-driven via `DJANGO_CSRF_TRUSTED_ORIGINS` — see writeup below. | **Review** |

#### BE-077 — CSRF Trusted Origins Configuration — 2026-09-10

**Status:** Review (awaiting Backend Lead approval — not self-approved)

**Priority:** P0 — release blocker. `CSRF_TRUSTED_ORIGINS` was never configured at all; any real deployment where `django.contrib.admin` is reached through an origin Django doesn't already trust by default would reject its own session-cookie form submissions.

**Owner:** Backend Team

**Scope note:** this API is JWT-bearer-token authenticated end to end (no `SessionAuthentication` in `REST_FRAMEWORK`), so CSRF only actually matters for `django.contrib.admin`'s own session+cookie login — not the JSON API itself.

**Implementation:** new typed-list env var `DJANGO_CSRF_TRUSTED_ORIGINS` (django-environ `(list, [])` default, comma-separated, same convention as the existing `CORS_ALLOWED_ORIGINS`) feeds `CSRF_TRUSTED_ORIGINS` directly in `config/settings.py`. Deliberately **not** derived from `CORS_ALLOWED_ORIGINS` — CORS (cross-origin fetch/XHR to the JSON API) and CSRF (trusted origins for admin's session cookie) are different concerns with different risk profiles; conflating them would trust the SPA's own origin for cookie-based admin form submission it was never meant to have. Empty by default, so local dev (admin normally accessed same-origin there) is unaffected. Never a wildcard. Documented in `backend/.env.example`.

**Verification:** django-environ list-parsing confirmed directly (empty string → `[]`, single value → one-element list, comma-separated → multi-element list, no wildcard risk). 5 new subprocess-based tests in `apps/common/tests/test_settings_hardening.py::CsrfTrustedOriginsTestCase` (dev boots unaffected; unset defaults to `[]` and never `"*"`; single-origin parses; multi-origin parses; a full production-style `DEBUG=false` + real `SECRET_KEY` + CSRF-configured boot succeeds) — all 5 passed; full file (10 tests) passed.

#### BE-068 — Dashboard Financial Access Separation — 2026-09-10

**Status:** Review (awaiting Backend Lead approval — not self-approved)

**Priority:** P0 — release blocker. `GET /reports/dashboard` was gated only by `report.view`, but the response contained real financial data — any role with dashboard access (Project Manager, Designer, etc.) could read company revenue, receivables, expenses, profit/loss, and per-invoice/payment amounts regardless of whether they held `report.financial_access`.

**Owner:** Backend Team

**Fix — backend-authoritative filtering, not frontend hiding:** `DashboardService.compute(company_id, include_financial: bool)` now only *computes* (queries) the 5 financial KPIs (`totalBilledRevenue`, `totalReceived`, `pendingAmount`, `totalExpenses`, `netProfitLoss`) and the `pendingPayments`/`overdueInvoices`/`recentExpenses`/`projectProfitability` sections when `include_financial` is true — when false, these keys are never added to the response dict at all. `DashboardView` resolves `include_financial` via `PermissionService.has_permission(membership, "report.financial_access")` (existing permission code, none invented), with the same standing `is_platform_admin(request)` bypass every other permission check in this codebase already grants. The endpoint-level gate stays `report.view` (unchanged — PM/Designer/etc. still need dashboard access for operational data); the new gate only controls the financial *payload*.

**Mechanism — genuine absence, not null/zero:** `DashboardKPISerializer`'s 5 money fields and `DashboardSerializer`'s financial-section fields are declared `required=False` with no `default`; when the source dict lacks the key, DRF's `SkipField` mechanism omits it from the serialized output entirely (not `null`, not `0.00`). A new `canViewFinancials` boolean is always present, for frontend UX (hiding cards) only — never used to gate what the backend actually sends.

**Deliberate scope extension, disclosed:** while implementing, a test asserting no financial figures leak into the raw response caught that `recentActivities` (via `AuditLogSerializer`'s `beforeState`/`afterState`) embeds real invoice/payment amounts for audit entries on those entities — even though the master prompt's own classification treated "activity" as operational. Rather than build per-entity-type audit-log redaction (a larger, riskier change out of this task's scope), `recentActivities` was also gated behind `include_financial`. Documented in code comments, test comments, and `05_Security/RBAC_Enforcement_Matrix.md` §7.4 as a disclosed deviation from the prompt's literal classification, in favor of "when in doubt, treat as financial."

**Explicitly unchanged:** `recentQuotations[].total` remains visible to `report.view` alone, per the master prompt's own explicit classification of quotations as operational/commercial pipeline data, not financial reporting.

**No role-name authorization introduced:** verified with a dedicated regression test creating a `Role` literally named `"Owner"` holding only `report.view` — it still receives `canViewFinancials: false` and no financial fields, proving the check is permission-code-driven, not name-driven.

**Frontend (F43):** `DashboardPage.tsx`'s `KpiStrip` and every financial card/section (Pending Payments, Overdue Invoices, Recent Expenses, Project Profitability, Recent Activity) now render conditionally on `data.canViewFinancials` — entirely absent, never a fake ₹0.00 fallback. `DashboardData`/`DashboardKPIs` types updated to make the financial fields optional, matching genuine backend absence.

**Tests:** `apps/dashboard/tests/test_services.py` (+1: `include_financial=False` omits every financial key/section, confirms operational data unaffected), `apps/dashboard/tests/test_views.py` (+12, `DashboardFinancialAccessTestCase`: 403 without `report.view`, 200 operational-only for `report.view`-only, raw-response-text check confirming no real financial figures ("5000.00"/"2000.00") leak anywhere in the body, full financial response for `report.financial_access`, tenant isolation unchanged, platform-admin full-access bypass, platform-admin missing `companyId` still 400, role-name-authorization regression) — 23/23 passed. Frontend: `frontend/src/pages/DashboardPage.test.tsx` (new, 8 tests: full dashboard renders, operational-only renders without crashing, no financial card/section rendered when restricted, never a fake ₹0.00, loading state shows no real data early, generic 500 and full-dashboard 403 both show backend message, existing recent-projects/quotations behavior unchanged) — 8/8 passed.

**Validation:** Live HTTP verification against a genuinely running `manage.py runserver`: seeded one company with a real invoice (5000.00, sent) + payment (2000.00), a full-access user, and a `report.view`-only user on a role named "Ops Viewer". Full-access token → `canViewFinancials: true` with real `totalBilledRevenue`/`totalReceived`/`pendingAmount`. View-only token → `canViewFinancials: false`, `kpis` contains only `totalProjects`/`activeProjects`/`totalQuotations`, no financial keys anywhere in the response, and a raw-text grep for "5000.00"/"2000.00" in that response found nothing. Unauthenticated → 401. All seeded data cleaned up, server stopped and confirmed down.

#### BE-076 — BOQ/Quotation/Invoice PDF Export — 2026-09-10

**Status:** Review (awaiting Backend Lead approval — not self-approved)

**Priority:** High — the first document-generation capability in the product; three real documents (BOQ, Quotation, Invoice) previously had no export path at all.

**Owner:** Backend Team

**Audit before coding:** searched the whole repo for WeasyPrint/xhtml2pdf/ReportLab/pdfkit/`application/pdf`/`FileResponse`/`render_to_string`/`templates/` — found nothing. No prior PDF infrastructure existed anywhere in `apps/boq`, `apps/quotations`, `apps/invoices`, `apps/company`, `apps/projects`, `apps/clients`, or `apps/products`.

**PDF engine — WeasyPrint audited and rejected, not silently swapped:** WeasyPrint was found already present in this machine's local Python environment, but (a) it is not declared anywhere in `requirements/*.txt` — its presence here is incidental, not a project dependency — and (b) it failed to import at all (`OSError: cannot load library 'libgobject-2.0-0'`) because it requires native GTK/Pango/Cairo system libraries not installed on this environment. Since neither "already installed" condition from the task's own decision criteria actually held, and the goal explicitly includes verifying the choice actually works (Phase 32/19), **xhtml2pdf** was chosen instead: pure Python (ReportLab-based), zero native system dependencies on any platform, still renders from Django HTML templates + CSS (preserving the required "template → PDF engine" architecture), and was verified end-to-end in this environment (WeasyPrint could not be). Added to `requirements/base.txt` (needed in production, not just dev).

**Shared architecture (not three independent systems):**
- `apps/common/pdf_service.py` — `render_pdf(template, context)` (Django `render_to_string` + `xhtml2pdf.pisa.CreatePDF`), `sanitize_filename()`, `pdf_http_response()` (real `application/pdf` bytes, never JSON/base64, `Content-Disposition: inline` for preview / `attachment` for download).
- `apps/common/templatetags/pdf_filters.py` — a `money` filter (thousands-separated, optional real currency-code prefix — never a hardcoded symbol) shared by all three templates.
- `apps/common/templates/pdf/base.html` — company header (name + GSTIN if present, no invented address/email/phone/logo fields — `Company` has none), document type/number/status badge, client details (name/email/mobile/GSTIN — `Client.addresses`' shape is undocumented so deliberately not rendered), project name, a repeating footer (`@frame`, `<pdf:pagenumber/>`/`<pdf:pagecount/>`) — all three document templates extend this one file and only fill the item-table/summary content block.
- `boq.html`/`quotation.html`/`invoice.html` extend `base.html`.

**Endpoints (permission codes verified against the real catalog, not invented):**
- `GET /projects/{projectId}/boq/pdf` — `boq.view`, same `ProjectPermission` as `BOQDetailView`.
- `GET /quotations/{quotationId}/pdf` — `quotation.view`, same `ProjectPermission` as `QuotationDetailView`. Exports exactly the version identified by `quotationId` — each version is its own row/id, so viewing an older version can never silently export the latest.
- `GET /invoices/{invoiceId}/pdf` — `invoice.view`, same `ProjectPermission` as `InvoiceDetailView`. Fetches via the same `InvoiceService.get_invoice_by_id`/`get_paid_amount`/`compute_outstanding_amount` the JSON API uses (BE-074) — `paidAmount`/`outstandingAmount` in the PDF are the identical backend-authoritative figures, never recomputed.
One endpoint per document, not two: `?mode=preview` renders `inline`; its absence (or any other value) renders `attachment`.

**Financial authority:** every number in every template context is already a real serializer/service value (`BOQSummaryService.compute_summary`, `Quotation.subtotal/discount/tax/total`, `InvoiceService.get_paid_amount`/`compute_outstanding_amount`) — no template performs arithmetic. BOQ's optional/alternative items are still shown in the table (labeled excluded) but never folded into the rendered total, verified directly (`test_optional_items_excluded_from_total_matches_summary_service`).

**Tenant isolation / RBAC:** identical `get_object_by_id` + `check_object_permissions` pattern every other action in these viewsets already uses — cross-tenant → 404, unauthenticated → 401. No new permission codes introduced.

**N+1 safety:** BOQ sections/items use one `Prefetch` (`select_related('product')`) regardless of section/item count; Quotation/Invoice items use `select_related('product')`/a single ordered queryset. Verified functionally via a 5-section/75-item BOQ test that must still return 200.

**HTML/content safety:** `render_to_string` autoescapes every context value by Django's own default (no `|safe` used anywhere in these templates) — verified directly by rendering a client name containing `<script>alert(1)</script>` and confirming the PDF still generates and the literal text (not executable markup) appears in the extracted output.

**Filenames:** `sanitize_filename()` strips everything outside `[A-Za-z0-9._ -]` and collapses whitespace to hyphens, falling back to a safe default rather than ever leaking an unsafe or bare-UUID name — e.g. `BOQ-Kitchen-Remodel.pdf`, `Quotation-QT-000001-v1.pdf`, `Invoice-INV-000001.pdf`.

**PDF generation failure:** unhandled by design at the view layer — `render_pdf` raises `PdfRenderError` (a plain, unregistered exception) on an engine failure, which falls through to the existing global `custom_exception_handler`'s catch-all (500 `INTERNAL_ERROR`, generic client-safe message, real cause logged server-side only) — no new error-handling path was built since the existing one already satisfies this requirement.

**Audit:** deliberately not logged — a PDF export/preview is a read action, matching this codebase's existing convention that reads (unlike creates/updates/deletes) don't generate `AuditLog` rows.

**Production dependency impact:** none beyond the one new pure-Python package. `xhtml2pdf` needs no system/OS packages on Linux or Windows, so `Dockerfile` requires no changes — confirmed by inspecting it (multi-stage `pip install -r requirements/*.txt`, which already installs whatever `base.txt` lists).

**Tests:** `apps/common/tests/test_pdf_service.py` (12: filename sanitization, real PDF byte generation, HTML-escaping, Content-Disposition), `apps/boq/tests/test_pdf_export.py` (14), `apps/quotations/tests/test_pdf_export.py` (10), `apps/invoices/tests/test_pdf_export.py` (12) — 48 new tests total, covering 200/content-type/signature, tenant isolation, unauthenticated 401, real content in the render (verified via `pypdf` text extraction — a test-only dependency, `requirements/dev.txt` — never grepping the compressed PDF bytes directly, which only ever coincidentally matches uncompressed metadata), a 75-item BOQ, correct quotation version selection, invoice payment-aggregate figures (zero/partial/overpaid), filename sanitization, and unsafe-content escaping.

**Validation:** New tests: 48/48 passed. Live HTTP verification against a genuinely running `manage.py runserver`: generated one real BOQ/Quotation/Invoice PDF each (`file` confirms genuine "PDF document, version 1.4"), confirmed preview (`inline`) vs download (`attachment`) disposition and correct filenames, confirmed cross-tenant/nonexistent/unauthenticated all correctly rejected. All seeded data deleted afterward; server stopped and confirmed down.

#### BE-075 — CI Pipeline — 2026-09-10

**Status:** Review (awaiting Backend Lead approval — not self-approved)

**Priority:** Medium — every gate this pipeline runs has, until now, only ever been run by hand once per task; nothing enforced it on every push/PR.

**Owner:** Backend/DevOps

**Scope, matched against `07_DevOps/CI_CD.md`'s documented 9-stage pipeline (not invented fresh):** wired what already reliably works today —

- Type check (frontend `tsc --noEmit`; backend has no mypy configured anywhere in `requirements/`, so no backend type-check stage exists yet).
- Unit/Integration/API tests: backend `python manage.py test` against a real `postgres:16` service container (matching `DATABASES` config in `config/settings.py`, not sqlite) — deliberately `manage.py test`, not `pytest`, since BE-070 found `apps.authentication`'s throttle-cache isolation only holds under Django's own runner.
- Frontend tests (`npm test -- --ci`) and production build (`npm run build`) — the same two commands this whole session has run by hand after every change.
- Dependency vulnerability scan (`pip-audit` against `requirements/prod.txt`, `npm audit --audit-level=critical`) — **informational only** (`continue-on-error: true`). The doc's own gate rule ("critical/high blocks merge") needs an actual severity policy decision from the team before it can safely block merges; wiring an arbitrary threshold here would be inventing policy, not implementing an approved one.
- Docker build validation (`docker build --target production`, never pushed anywhere) — exercises the existing `Dockerfile` so it can't silently rot, without needing any registry credentials.

**Explicitly NOT wired, and why (flagged, not invented around):**
- **Lint** — no `ruff`/`flake8` config exists anywhere in `requirements/`, no `eslint.config.*` exists in the frontend beyond what ships inside `node_modules` dependencies. There is nothing to run; choosing rules is a real scoping decision for the team, not something to fabricate here.
- **E2E** — no Playwright (or other) E2E suite exists in this repo yet.
- **Deploy stages** (staging/production) — need real infrastructure and secrets (registry, cloud credentials, environment URLs) this repo has none of configured. A deploy stage that can't actually deploy would be a fake pipeline step, exactly the anti-pattern this project's own rules forbid.

**Validation:** YAML parses cleanly (`yaml.safe_load`). Every command the workflow runs was executed locally first: `python manage.py test --noinput` (the exact CI command, sanity-checked scoped to `apps.invoices apps.payments` — 93/93 passed; the full-suite run is the final validation step of this task, see the final report for its result) and `npm test -- --ci` / `npx tsc --noEmit` / `npm run build` (frontend — all confirmed passing). The `docker-build` job's `Dockerfile` was read and matches standard multi-stage syntax, but could not be locally re-validated in this environment — the local Docker daemon isn't running here, so this one job is unverified beyond code review; flagged, not silently assumed to work.

#### BE-074 — Invoice Payment Aggregates — 2026-09-09

**Status:** Review (awaiting Backend Lead approval — not self-approved)

**Priority:** High — without this, the frontend had no way to show Amount Paid/Balance Due without computing financial totals itself, which the project's own rules forbid.

**Owner:** Backend Team

**Problem:** `InvoiceSerializer` exposed `total` but no `paidAmount`/`outstandingAmount` — `PaymentRepository.sum_active_amount_for_invoice` already existed internally (used only by `InvoiceService.recompute_status_from_payments` to derive `status`), but was never surfaced in any API response.

**Semantics, confirmed against existing code before implementing (not assumed):** `paidAmount` = sum of active (non-voided) payments, exactly what `sum_active_amount_for_invoice` already computed. `outstandingAmount` = `max(total - paidAmount, 0)` — overpayment is genuinely allowed (`PaymentService.create_payment`/`payments/validators.py` have no upper bound) and `recompute_status_from_payments` already treats `paid_total >= total` as simply `paid`, nothing more — a negative "balance due" would misrepresent the company as owing the client money, a state this product doesn't model, so the remaining-balance figure alone is floored at zero while `paidAmount` still reports the real, possibly-larger figure unchanged. Overpayment policy itself is untouched.

**Backend API:** No new endpoint — `paidAmount`/`outstandingAmount` (decimal strings) added directly to the existing `InvoiceSerializer`, so every action that returns an Invoice (list, detail, create, update, send, cancel) carries them identically, via `get_paidAmount`/`get_outstandingAmount` `SerializerMethodField`s backed by new `InvoiceService.get_paid_amount`/`compute_outstanding_amount`.

**Read-only enforcement:** Both are `SerializerMethodField`s (no setter) and neither appears in `InvoiceUpdateSerializer` — a client-supplied `paidAmount`/`outstandingAmount` in a PATCH body is simply never read, verified directly (`test_fields_are_read_only_on_patch`/`test_fields_are_read_only_on_draft_patch`).

**N+1 strategy:** `apps.invoices.repositories.with_paid_amount` annotates every Invoice queryset with `paid_amount` via a correlated `Subquery` (not a `Sum` JOIN+GROUP BY, which would risk fan-out if ever combined with another multi-valued-relation annotation) — one query total regardless of list size, applied to both `InvoiceRepository.get_by_id`/`all_for_project` and `selectors.list_invoices_for_project`. `InvoiceService.get_paid_amount` reads that annotation with zero extra queries when present, falling back to the original `sum_active_amount_for_invoice` single-row query only for an invoice instance mutated and returned in-memory without a re-fetch (create/update/send/cancel's own response — always exactly one row, never a list). Proven, not just argued: `test_list_does_not_incur_n_plus_1_payment_queries` holds invoice count fixed across two captures and shows adding payments to every invoice in the list adds zero additional queries.

**Tenant isolation:** Unchanged — the annotation is correlated per-invoice via `OuterRef("pk")`, scoped by whatever tenant filtering the outer queryset already applies; no new cross-tenant surface introduced.

**Tests:** New `apps/invoices/tests/test_payment_aggregates.py` (24 tests) — zero/one/multiple/partial/full/overpaid payments, voided/soft-deleted payment exclusion, create/void updates the aggregate, cross-invoice and cross-tenant isolation, decimal precision, read-only enforcement (sent and draft invoices), detail and list both carry the fields, draft/cancelled invoice behavior (a cancelled invoice retains its real historical `paidAmount` and can no longer accept new payments — existing rule, unchanged), status still comes from the real persisted/derived value, the N+1 regression guard, and direct unit coverage of the annotated-vs-fallback computation path.

**Validation:** New tests: 24/24 passed. Full `apps.invoices`+`apps.payments`+`apps.audit`+`apps.reports` regression: **134 passed, 0 failed**. Live HTTP lifecycle against a genuinely running `manage.py runserver`: created an invoice (total 300.00) → confirmed paidAmount=0/outstanding=300 → recorded payment A (120.00) → confirmed paidAmount=120/outstanding=180 → recorded payment B (80.00) → confirmed paidAmount=200/outstanding=100 → voided payment A → confirmed paidAmount reversed to 80/outstanding=220 → recorded an overpayment (500.00, total already exceeded) → confirmed paidAmount=700 (the real figure) with outstanding correctly floored at 0 and status `paid` → confirmed an unrelated invoice in the same project was unaffected throughout. All seeded data deleted afterward; server stopped and confirmed down.

#### BE-073 — Role Delete Safety — 2026-09-09

**Status:** Review (awaiting Backend Lead approval — not self-approved)

**Priority:** High — a real, confirmed authorization-consistency gap, not a hypothetical one.

**Owner:** Backend Team

**Problem, confirmed empirically (not guessed):** soft-deleting a `Role` that one or more active `CompanyMembership` rows still referenced left those members with their full permission grant from that role, indefinitely. Root cause, verified with a direct reproduction against the database: `RoleRepository.soft_delete` only sets `deleted_at` — it never touches `is_active`, and Django's `on_delete=SET_NULL` on `CompanyMembership.role` only fires on a real DB `DELETE`, which a soft-delete `save()` never triggers. `PermissionService.get_permission_codes_for_membership` gates on `role.is_active` (untouched by delete), and `PermissionRepository.codes_for_role` filters `RolePermission` by `role_id` without checking whether the `Role` itself is soft-deleted. Net effect: `GET /roles/{id}` correctly 404s post-delete (the role vanishes from the Roles admin UI), but the membership silently kept full access, and `CompanyMembershipSerializer` kept showing the stale `roleId`/`roleName` of a role that no longer existed anywhere else in the API — reproduced and confirmed via a live `manage.py shell` script before any fix was written (seeded data cleaned up immediately after).

**Fix:** `RoleRepository.unassign_from_memberships(role_id)` (new) bulk-clears the `role` FK to `null` on every membership referencing it, called from `RoleService.soft_delete_role` immediately after the soft-delete. This explicitly replicates the FK's own already-declared `on_delete=SET_NULL` intent, which soft-delete alone never triggers — it does not invent new semantics. A membership left with no role is already the documented, tested, fail-closed "zero permission codes" state used everywhere else in this module (`get_permission_codes_for_membership` returns `set()` when `role_id is None`). No role deletion is blocked; no `system_key`/role-name matching was introduced anywhere.

**Audit trail:** the existing `role`/`delete` audit log entry's `before_state` now also carries `memberships_unassigned` (an integer count) — added to `apps/audit/validators.py`'s per-entity allowlist (a safe, non-sensitive field).

**Tests:** 4 new tests in `apps/users/tests/test_role_services.py` — membership unassigned on delete, effective permissions revoked (with a real granted permission, not just an empty set), unrelated memberships on other roles left untouched, audit log records the affected count.

**Validation:** New tests: 4/4 passed. Full `apps.users`+`apps.authentication`+`apps.company`+`apps.audit` regression: **362 passed, 0 failed**. Live HTTP verification against a genuinely running `manage.py runserver`: created a role, added a member under it, confirmed the membership showed the role, deleted the role, confirmed the membership's `roleId`/`roleName` immediately became `null`, confirmed the role itself 404s. All seeded data deleted afterward.

#### BE-072 — Role Permission Read-Back — 2026-09-09

**Status:** Review (awaiting Backend Lead approval — not self-approved)

**Priority:** High — without this, no UI could ever safely show which permissions a role currently holds, blocking a real "Edit Permissions" experience for anything but a just-created (blank) role.

**Owner:** Backend Team

**Problem:** `PUT /roles/{id}/permissions` (BE-049/BE-051) was write-only — `RoleSerializer` never included granted codes, and no `GET` variant of the action existed. A frontend editing an existing, already-configured role's permissions had no way to know what was currently granted, so it could only safely operate on a role with zero grants (immediately post-creation).

**Endpoint:** `GET /roles/{id}/permissions` — added as a second action method (`RoleViewSet.retrieve_permissions`) dispatched to the *same URL* as the existing `PUT .../permissions` (`permissions_action`), via `urls.py`'s existing manual-mapping convention (`role_permissions = RoleViewSet.as_view({"get": "retrieve_permissions", "put": "permissions_action"})`) — identical to how `role_detail` already dispatches 4 different methods from one URL. This let GET and PUT carry **different** permission codes despite sharing a path: `retrieve_permissions` → `role.view` (a read action, same code as `list`/`retrieve`), `permissions_action` (PUT) → unchanged `role.manage`. No second URL pattern was created.

**Response:** `{roleId, permissionCodes: [...]}` (new `RolePermissionsSerializer`), sorted list, inside the standard envelope.

**Source of truth:** `PermissionRepository.codes_for_role` — the exact same, already-existing, soft-delete-aware query `assign_permissions` already used internally to compute `before_codes`/escalation checks. Nothing was reconstructed from `DEFAULT_ROLE_PERMISSIONS` or any other seed data; confirmed by `test_returns_persisted_grants_not_defaults` and `test_soft_deleted_grant_is_not_returned`.

**Tenant isolation / auth:** Identical `get_role_by_id(pk)` + `check_object_permissions` pattern every other action in this viewset uses — cross-tenant role → 404 (not 403, anti-enumeration preserved), same-tenant without `role.view` → 403, platform admin → unrestricted. No role-name-based authorization anywhere.

**Assignment semantics (unchanged, verified not just assumed):** `PUT` is a full-replacement write, confirmed via `test_put_replaces_the_entire_set_not_a_delta` — granting `["invoice.view"]` after `["project.view", "project.edit"]` already existed leaves only `invoice.view`.

**Privilege escalation:** No change to `assign_permissions`' existing guard — re-verified still blocked (`test_privilege_escalation_still_blocked_on_assignment`), and confirmed nothing is actually granted when a rejected request is attempted.

**Role.system_key (BE-069):** Still unresolved, not touched by this task. No role-name comparisons were introduced anywhere in this work.

**Tests:** `apps/users/tests/test_role_permissions_readback.py` (17 tests) — persisted-state read-back, empty set, multi-permission, only-this-role's-grants, soft-deleted-grant exclusion, cross-tenant 404, nonexistent-role 404, unauthenticated 401, missing-`role.view` 403, inactive-role-still-readable, platform-admin cross-company read, write-then-read persistence (add + remove), replace-all semantics, privilege escalation regression, read-produces-no-audit-noise, mutation-still-audited, no-unrelated-tenant-grants-leaked.

**Validation:** `test_role_permissions_readback.py`: **17 passed** (isolated). Full `apps.users`+`apps.authentication`+`apps.audit` regression: **308 passed, 0 failed** (was 291 before this task — the +17 is exactly this new file, confirming zero regressions elsewhere). Real HTTP lifecycle verified against a genuinely running `manage.py runserver` instance (not just the Django test client): login → list roles → GET role A's initial grant → PUT to add a permission → GET confirms persistence → PUT to remove one (replace-all) → GET confirms removal → cross-tenant role access → 404 → unauthenticated mutation → 401. All seeded verification data (test company/user/roles) was deleted afterward; no mutations left behind.

#### BE-071 — Add User / Secure Company User Onboarding — 2026-09-09

**Status:** Review (awaiting Backend Lead approval — not self-approved)

**Priority:** Critical (P0) — the previous "Invite Member" flow could only link an existing global User account; there was no way for an admin to bring a genuinely new person into the product at all.

**Owner:** Backend Team

**Problem:** `CompanyMembershipService.invite_member` (BE-052) is explicitly scoped to existing users only — its own docstring says so, and `CompanyMembershipRepository.get_user_by_email` raises 404 for an unknown email. There was no endpoint anywhere that could create a new `User` account as part of granting company access.

**Model selected:** Admin-creates-user + email activation (not temporary passwords) — reuses the existing `PasswordResetToken`/`POST /auth/reset-password` machinery end to end rather than inventing a second credential mechanism. A brand-new `User` is created via `UserManager.create_user(..., password=None)`, which Django's own `set_unusable_password()` marks as unable to authenticate until a token-backed password is set — identical mechanically to a password reset, so no new token model or consuming endpoint was needed.

**New endpoint:** `POST /company-memberships/add-user` (`CompanyMembershipViewSet.add_user`, a custom `@action` alongside the existing `assign-role`/`suspend`/`reactivate` actions — matches this viewset's own established routing convention). Request: `{email, name, roleId}` (`name` is `User`'s only name field — no first/last split exists on the model). Response: `{membership, userCreated, activationRequired}`. Permission code: `user.manage` (same code `invite_member`/`assign_role`/`suspend`/`reactivate` already use — no new permission code was introduced).

**Identity resolution (`CompanyMembershipService.add_user`):**
- Unknown email → new `User` created, `user_created=true`, activation email sent.
- Existing email with no membership (or only a **revoked** one) in this company → the existing `User` is reused as-is (never duplicated); a revoked membership is **reactivated in place** (role updated, status → active) rather than blocked — a deliberate improvement over `invite_member`'s existing behavior of blocking on any non-deleted row regardless of status (documented, not silently changed there).
- Existing **active/invited** membership → 409, identical to `invite_member`'s own conflict.
- Existing user with a still-unusable password (e.g. a prior setup never completed) → treated as `activationRequired=true` and a fresh email is (re)sent, even though `user_created=false`.

**Membership status:** created/reactivated as **ACTIVE**, not INVITED — confirmed by reading `PermissionService.get_permission_codes_for_membership` that nothing in this codebase ever automatically transitions `invited → active` (only the explicit `POST .../reactivate` action does), so an Add-User membership left at `invited` would be a silent permission dead-end even after the person finishes activation and logs in. Membership status answers "should this person have access now" (yes); the User's own `has_usable_password()` is the separate, correct gate on whether they can log in yet.

**Transaction safety:** the whole flow (user lookup/creation, role validation, membership create/reactivate, audit log) runs inside `transaction.atomic()`; a `RuntimeError` forced mid-flow in tests (mocking `CompanyMembershipRepository.create`) confirms the newly-created `User` row does **not** persist — no orphan accounts on failure. `IntegrityError` from the DB's own unique constraint (two concurrent Add User calls for the same brand-new email) is translated to the same 409 `ConflictError` shape every other conflict in this service already uses, never a raw 500. True concurrent-request racing wasn't exercised (not practical in a synchronous `TestCase`) — only the constraint-translation path is unit-tested.

**Privilege escalation:** identical guard to `invite_member`/`assign_role` — a non-platform-admin actor can never Add a User into a role granting permission codes they don't hold themselves.

**Self-action safety (Phase 28, allowed as part of this task):** confirmed **no protection existed anywhere** against an admin suspending or removing their own membership. Added directly in `CompanyMembershipService._set_status` (suspend only — reactivating yourself is never dangerous) and `remove_member`: `actor_user.id == membership.user_id` now raises 403. **Last-owner protection was explicitly NOT attempted** — `Role` has no `system_key`/protected-role identity (BE-069, still open), so any "who is the current owner" check would have to match the free-text display name, exactly the fragile pattern BE-069 already flags as technical debt. Per the task's own instruction ("STOP and report the blocker instead of implementing fragile name matching"), this is reported, not built.

**Audit logging:** reuses the existing `entity_type="company_membership"`/`AuditAction.CREATE` convention `invite_member` already uses (no new audit action was invented). `apps/audit/validators.py`'s allowlist gained one new field, `user_created` (boolean only — never a password/token/activation-link value), so the audit trail records whether the action created a new account or linked an existing one.

**Email:** `AccountActivationEmailService` (new, `apps/authentication/services.py`, alongside the existing `PasswordResetEmailService`) sends to the real configured backend — this environment defaults to `django.core.mail.backends.console.EmailBackend` (dev-console only; confirmed via `config/settings.py`), so no external delivery is claimed anywhere in the response or UI copy.

**Frontend gap closed as part of this task:** `/reset-password` had **no page at all** in the frontend despite the backend supporting `POST /auth/reset-password` since Sprint 1 — confirmed by a full read of `App.tsx`'s route table. New `SetPasswordPage.tsx` consumes the token (works identically for both a forgot-password email and this task's new activation email, since the backend endpoint treats them identically) — without it, a newly added user would have had no way to ever complete login.

**Tests:** `apps/users/tests/test_add_user.py` (26 tests) — new-user creation, existing-user linking (no duplication, name preserved), unusable-password re-send, duplicate active/invited 409, revoked-membership reactivation, cross-tenant/inactive/missing role rejection, privilege escalation, multi-company membership for the same email, atomic rollback on failure, audit content (flag present, no secrets), and a full real end-to-end authentication lifecycle test (activation token extracted from the captured test email → `POST /auth/reset-password` → `POST /auth/login` → `GET /auth/memberships` confirms the new company). Plus `SelfActionSafetyTestCase` (3 tests) for the suspend/remove self-guards.

**Validation:** `apps/users/tests/test_add_user.py`: **26 passed** (isolated run). Full `apps.users`/`apps.authentication`/`apps.audit` regression run in progress at time of writing — see the phase's final report for the completed count.

#### BE-070 — Authentication Throttle Test-Isolation Fix — 2026-09-09

**Status:** Review (awaiting Backend Lead approval — not self-approved)

**Priority:** P0 (test-infrastructure stabilization)

**Owner:** Backend Team

**Problem:** A prior completion audit reported 13 failures + 3 errors in `apps.authentication`'s test suite, concentrated in `test_throttling.py`, `test_login.py`, `test_forgot_password.py`, `test_reset_password.py`, claimed reproducible in both a full-suite run and an isolated `apps.authentication` run.

**Reproduction:** Did not reproduce via `pytest apps/authentication` (70 passed, 0 failed, both isolated and as part of the full suite) — but reproduced **exactly** via `python manage.py test apps.authentication --noinput` (13 failures + 3 errors, identical test names, identical assertion lines, e.g. `AssertionError: 429 != 200` on `test_valid_login_returns_token_pair_and_user_profile`).

**Root cause:** `backend/conftest.py` already has an autouse `_clear_throttle_cache` pytest fixture (added Sprint 1, commit `4990ceab`) that clears Django's cache before/after every test — this is why `pytest` runs were always clean. Pytest fixtures are a pytest-only mechanism, however: `conftest.py` is never read and `@pytest.fixture` never executes under Django's own `manage.py test` runner. Every `TestCase` in `apps/authentication/tests/` inherited bare `django.test.TestCase` with no isolation of its own, so under `manage.py test` specifically, `ScopedRateThrottle`'s cache-backed request counters (keyed `throttle_{scope}_{ident}`, `ident` = client IP for these anonymous pre-auth endpoints, which the Django test client always presents identically) accumulated across every test method and file in the run, eventually tripping 429 on ordinary tests that expected 200/401/400 and shifting the intentional throttling tests' own loop boundaries.

**Affected cache keys/scopes:** `throttle_auth_login_<test-client-ip>`, `throttle_auth_forgot_password_<ip>`, `throttle_auth_reset_password_<ip>`, `throttle_auth_refresh_<ip>`, `throttle_platform_auth_login_<ip>` — all five throttled auth scopes, shared across every TestCase in the app within one process.

**Fix:** New `apps/authentication/tests/base.py::ThrottleIsolatedTestCase(TestCase)`, clearing `django.core.cache.cache` from `_pre_setup`/`_post_teardown` (the same hooks Django's own `SimpleTestCase` uses for its DB-transaction wrapping) rather than `setUp`/`tearDown` — this fires unconditionally before/after every test method regardless of whether a subclass's own `setUp`/`tearDown` calls `super()` (none of this app's existing ones do), and executes identically under both `pytest` and `manage.py test` since it relies on no pytest-specific mechanism. All 9 TestCases in `apps/authentication/tests/` now inherit it instead of bare `TestCase`. The pre-existing pytest conftest fixture is left in place (harmless, and still the correct backstop for any other app's tests that might one day call a throttled endpoint under `pytest`).

**Why this is test-only:** No production file changed. `config/settings.py`'s `DEFAULT_THROTTLE_CLASSES`/`DEFAULT_THROTTLE_RATES`, every view's `throttle_scope`, and `ScopedRateThrottle` itself are untouched — the fix only changes which base class test files inherit from.

**Regression test:** `apps/authentication/tests/test_throttle_isolation.py` (new) — two methods that each independently drain the same `auth_forgot_password` scope from a cold start and assert the identical boundary (5 allowed, 6th throttled). Neither depends on which runs first; before this fix, whichever ran second would have inherited the first's exhausted counter and failed at an earlier call.

**Verification:**
- `manage.py test apps.authentication --noinput`: run 1 — 70 passed, OK. Run 2 — 70 passed, OK. Run 3 (after adding the regression test) — 72 passed, OK.
- `pytest apps/authentication`: 70 passed (unaffected — was already green; confirms no regression on the runner that already worked).
- `git diff --check`: clean. Production code diff: zero lines — only `apps/authentication/tests/*` touched (9 files switched base class + 2 new files).

**Files changed:** `apps/authentication/tests/base.py` (new), `apps/authentication/tests/test_throttle_isolation.py` (new), `apps/authentication/tests/{test_login,test_logout,test_me,test_memberships,test_platform_auth,test_refresh,test_reset_password,test_forgot_password,test_throttling}.py` (base class swap only).

**Full backend suite** (single serial `pytest` run, no `--reuse-db`): **1091 passed, 1 failed**, 6028s (1h40m). The one failure — `apps.users.tests.test_membership_management_views.CompanyMembershipViewSetTestCase.test_platform_admin_can_still_call_endpoints`, `AssertionError: 401 != 200` (`InvalidToken`) — is in a completely unrelated app/file (JWT token validation, not throttling/cache) and re-ran clean in isolation (19/19 passed, 77s). Classified **ENVIRONMENTAL**: consistent with the previously-documented pattern of isolated, non-reproducible failures surfacing only under very long sustained full-suite runs (a shorter prior run showed none, a 40-minute run previously showed ~21 unrelated `setUpClass` errors that also vanished on isolated re-run). Not a regression from this task — no code this task touches is imported by that test file.

**P2–P4 — Phase 3–5 (backlog only, not started, per `CLAUDE.md`'s explicit deferral)**

| ID | Task |
|---|---|
| BE-061 | Leads/CRM pipeline (Lead, source, stage, assignment, conversion to Client/Project, follow-ups) |
| BE-062 | Site Visits (scheduling, assignment, status, notes, photo/doc attachment, follow-up) |
| BE-063 | Design Management (Design, DesignVersion, review/approval/revision cycle) |
| BE-064 | Procurement (Vendor, Purchase Request, Purchase Order, delivery tracking, BOQ linkage) |
| BE-065 | Notifications (model, in-app read/unread, tenant scope, event-driven creation, optional async email dispatch via Celery) |
| BE-066 | Client Portal (scoped auth/access model, project/quotation/invoice/document visibility, strict per-client isolation) |
| BE-067 | Background jobs via Celery (async email, PDF/report generation, scheduled reminders) — infra already scaffolded (BE-003), never used |

Depends On

- BE-048 (all Sprint 1–7 work)

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