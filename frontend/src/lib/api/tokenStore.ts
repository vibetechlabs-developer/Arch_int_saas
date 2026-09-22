const ACCESS_KEY = 'accessToken';
const REFRESH_KEY = 'refreshToken';
const AUTH_MODE_KEY = 'authMode';

// A platform admin authenticates via a completely separate endpoint
// (POST /platform-auth/login) that mints a distinct token type — the JWT
// itself carries no company scope either way (TenantJWTAuthentication
// resolves that per-request, never from the token). `authMode` just
// remembers which login flow issued the tokens currently in storage, so a
// page refresh can restore the right session type without guessing.
export type AuthMode = 'company' | 'platform';

export const tokenStore = {
  getAccessToken: (): string | null => localStorage.getItem(ACCESS_KEY),
  getRefreshToken: (): string | null => localStorage.getItem(REFRESH_KEY),
  getAuthMode: (): AuthMode | null => {
    const mode = localStorage.getItem(AUTH_MODE_KEY);
    return mode === 'company' || mode === 'platform' ? mode : null;
  },
  setTokens: (accessToken: string, refreshToken: string, mode: AuthMode = 'company'): void => {
    localStorage.setItem(ACCESS_KEY, accessToken);
    localStorage.setItem(REFRESH_KEY, refreshToken);
    localStorage.setItem(AUTH_MODE_KEY, mode);
  },
  clear: (): void => {
    localStorage.removeItem(ACCESS_KEY);
    localStorage.removeItem(REFRESH_KEY);
    localStorage.removeItem(AUTH_MODE_KEY);
  },
};
