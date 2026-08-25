# Authentication API (Draft)
## INT Projects — Multi-Company Interior & Architecture Management SaaS

**Status:** Draft endpoint sketch — request/response payload schemas pending backend framework selection (`02_Architecture/Technical_Architecture.md` §8).

---

## Scope

Covers login/session management for both **company users** and the **Platform Super Admin** (kept architecturally separate per `02_Architecture/Technical_Architecture.md` §4), plus user invitation/onboarding.

## Endpoints

| Method | Path | Purpose | Auth Required |
|---|---|---|---|
| POST | `/auth/login` | Company user login (email + password) | No |
| POST | `/auth/logout` | Invalidate current session/token | Yes |
| POST | `/auth/forgot-password` | Trigger password reset email | No |
| POST | `/auth/reset-password` | Complete password reset with token | No |
| POST | `/auth/verify-email` | Confirm email via verification token | No |
| POST | `/auth/refresh` | Exchange refresh token for new access token | Refresh token |
| GET | `/auth/me` | Current user identity + company memberships | Yes |
| POST | `/platform-auth/login` | Platform Super Admin login (separate surface) | No |

## User Invitation / Membership

| Method | Path | Purpose | Permission |
|---|---|---|---|
| POST | `/companies/{companyId}/users/invite` | Invite a user to the company (creates `company_membership` in `invited` status) | `user.manage` |
| POST | `/invitations/{token}/accept` | Accept invite, set password, activate membership | No auth (token-based) |
| PATCH | `/companies/{companyId}/users/{userId}/status` | Activate/deactivate a membership | `user.manage` |
| POST | `/companies/{companyId}/users/{userId}/reset-password` | Admin-initiated password reset | `user.manage` |

## Notes

- A successful `/auth/login` response returns the user identity **and their list of company memberships**, but **not** an implicit "current company" — the frontend must explicitly select/confirm a company context per session, and every subsequent request must resolve tenant scope server-side from the membership record for that selected company, never from a client-supplied company ID (see `05_Security/Tenant.md`).
- 2FA endpoints are out of scope for MVP (source doc lists 2FA as "optional in future" — `01_Business/FRS.md` §3).
- Platform Super Admin tokens must carry a distinct claim/scope that company-user tokens never receive, so a leaked company-user token can never be replayed against platform-admin endpoints.
