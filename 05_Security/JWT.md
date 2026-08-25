# JWT / Session Design (Draft)
## INT Projects — Multi-Company Interior & Architecture Management SaaS

**Status:** Draft proposal — final token library/format depends on the backend framework chosen (`02_Architecture/Technical_Architecture.md` §8).

---

## 1. Principle

The source requirements are explicit: **"The frontend must not be trusted to provide a company ID for authorization."** This directly shapes what belongs in the token and what must be re-resolved on every request.

## 2. What the Access Token Should Carry

- `sub` — user ID
- `email`
- `token_type` — `company_user` or `platform_admin` (kept structurally distinct so a leaked company-user token can never be replayed against a platform-admin endpoint)
- Standard claims: `iat`, `exp`, `jti` (for revocation support)

## 3. What the Access Token Must NOT Carry

- **Company/tenant ID** — even if a user has selected an "active company" in the frontend, the server must re-verify that user's membership in that company from the `company_membership` table on every request, not trust a claim in the token. This prevents a token issued under one company context from being replayed against another company's data if the client is compromised or a token is crafted.
- **Role/permissions** — roles can change (revoked, reassigned) after a token is issued; embedding them would let a revoked permission remain usable until token expiry. Resolve role/permission fresh from `company_membership` + `role_permission` on each request (or accept a short-lived cache with explicit invalidation on role change).

## 4. Token Lifecycle

- **Access token:** short-lived (e.g. 15 minutes), sent as `Authorization: Bearer`.
- **Refresh token:** longer-lived, stored httpOnly/secure cookie or equivalent, used only against `/auth/refresh`.
- **Logout / revocation:** refresh token must be invalidated server-side (denylist or rotation) — a stateless JWT alone cannot be "logged out," so refresh-token state must be tracked.

## 5. Company Context Selection

Since a user's token doesn't carry a company ID, the frontend must send the **currently selected company** explicitly on each request (e.g., as a path parameter `/companies/{companyId}/...` or a header), and the Tenant/Permission middleware validates that value against the user's actual memberships before proceeding — see `05_Security/Tenant.md`. If the value doesn't match an active membership, the request is rejected (403), not silently corrected.

## 6. Platform Super Admin Tokens

Issued via a separate `/platform-auth/login` endpoint (see `04_API/Authentication_API.md`), carrying `token_type: platform_admin` and no company context at all — platform endpoints operate above the tenant layer entirely.

## 7. Open Decisions

- Symmetric (HS256) vs. asymmetric (RS256) signing — RS256 recommended if the API layer is ever split into multiple services that need to verify tokens without sharing a signing secret.
- Refresh token rotation strategy (rotate-on-use vs. fixed refresh token with a denylist).
