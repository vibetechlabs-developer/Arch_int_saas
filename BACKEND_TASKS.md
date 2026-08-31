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

Status: In Progress — all tasks implemented (BE-022, BE-023, BE-024 Done; BE-025–BE-030 Review, awaiting Backend Lead approval)

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

**Status:** Review

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

**Status:** Review

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

**Status:** Review

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

**Status:** Review

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

**Status:** Review

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

**Status:** Review

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

Status: In Progress (BE-031, BE-032 Review; BE-033–BE-034 Todo)

---

### BE-031 – Categories

**Status:** Review

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

**Status:** Review

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

# Sprint 4 – BOQ

- BE-035 – BOQ Module
- BE-036 – BOQ Items
- BE-037 – BOQ Calculations
- BE-038 – BOQ APIs

Status: Todo

---

# Sprint 5 – Quotation

- BE-039 – Quotation
- BE-040 – Versioning
- BE-041 – Approval Workflow

Status: Todo

---

# Sprint 6 – Finance

- BE-042 – Invoice
- BE-043 – Payment
- BE-044 – Expense
- BE-045 – Financial Reports

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