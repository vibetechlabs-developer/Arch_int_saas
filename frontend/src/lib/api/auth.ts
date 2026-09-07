import { apiClient, unwrap } from './client';
import { tokenStore } from './tokenStore';

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

export async function logout(): Promise<void> {
  const refreshToken = tokenStore.getRefreshToken();
  tokenStore.clear();
  if (refreshToken) {
    try {
      await apiClient.post('/auth/logout', { refreshToken });
    } catch {
      // Best-effort: tokens are already cleared client-side either way.
    }
  }
}
