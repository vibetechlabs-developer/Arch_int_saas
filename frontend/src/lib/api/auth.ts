import { apiClient, unwrap } from './client';
import { tokenStore } from './tokenStore';
import { activeCompanyStore } from '@/lib/activeCompany';

// Matches apps/authentication UserSerializer exactly — no embedded
// company/role (see the two flagged gaps in the Milestone 1 plan).
export interface User {
  id: string;
  email: string;
  name: string;
  status: string;
  isActive: boolean;
  isStaff: boolean;
  createdAt: string;
  updatedAt: string;
}

interface LoginResponseData {
  accessToken: string;
  refreshToken: string;
  user: User;
}

export async function login(email: string, password: string): Promise<User> {
  const data = await unwrap<LoginResponseData>(apiClient.post('/auth/login', { email, password }));
  tokenStore.setTokens(data.accessToken, data.refreshToken);
  return data.user;
}

export async function fetchCurrentUser(): Promise<User> {
  return unwrap<User>(apiClient.get('/auth/me'));
}

// Mirrors backend/apps/authentication/serializers.py::MyMembershipSerializer
// — deliberately minimal (no roleId, no permission codes): just enough to
// label and select a workspace. Only active memberships are returned.
export interface MyMembership {
  companyId: string;
  companyName: string;
  status: string;
  roleName: string | null;
}

export async function fetchMyMemberships(): Promise<MyMembership[]> {
  return unwrap<MyMembership[]>(apiClient.get('/auth/memberships'));
}

// POST /auth/forgot-password requires only an email and works whether or
// not the caller is currently authenticated — there is no separate
// logged-in "change my password" endpoint, so the Security settings page
// reuses this same flow, pre-targeted at the current user's own email.
// Always returns the same generic message regardless of outcome
// (anti-enumeration), throttled at 5/min.
export async function requestPasswordReset(email: string): Promise<void> {
  await apiClient.post('/auth/forgot-password', { email });
}

// POST /auth/reset-password — consumes a single-use token (from either
// the forgot-password email or an Add User account-setup email; the
// backend treats both identically) and sets a new password. No prior
// authentication required.
export async function resetPassword(token: string, newPassword: string): Promise<void> {
  await apiClient.post('/auth/reset-password', { token, newPassword });
}

export async function logout(): Promise<void> {
  const refreshToken = tokenStore.getRefreshToken();
  tokenStore.clear();
  activeCompanyStore.set(null);
  if (refreshToken) {
    try {
      await apiClient.post('/auth/logout', { refreshToken });
    } catch {
      // Best-effort: tokens are already cleared client-side either way.
    }
  }
}
