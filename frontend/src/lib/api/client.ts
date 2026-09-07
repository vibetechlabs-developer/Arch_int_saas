import axios, { AxiosError, InternalAxiosRequestConfig } from 'axios';
import { tokenStore } from './tokenStore';

/**
 * Matches 00_Development_Standards/API_Response_Format.md exactly: every
 * success response carries `data` (+ `pagination` for list endpoints),
 * every error response carries `error.code`/`message`/`details`, and both
 * carry a `requestId` — the same envelope regardless of resource shape.
 */
export interface ApiEnvelope<T> {
  success: true;
  data: T;
  requestId: string;
}

export interface PaginationMeta {
  page: number;
  pageSize: number;
  totalItems: number;
  totalPages: number;
}

export interface PaginatedEnvelope<T> {
  success: true;
  data: T[];
  pagination: PaginationMeta;
  requestId: string;
}

export interface ApiErrorDetail {
  field: string;
  issue: string;
}

export interface ApiErrorEnvelope {
  success: false;
  error: { code: string; message: string; details: ApiErrorDetail[] };
  requestId: string;
}

export class ApiError extends Error {
  code: string;
  details: ApiErrorDetail[];
  requestId?: string;
  status?: number;

  constructor(code: string, message: string, details: ApiErrorDetail[] = [], requestId?: string, status?: number) {
    super(message);
    this.name = 'ApiError';
    this.code = code;
    this.details = details;
    this.requestId = requestId;
    this.status = status;
  }
}

const baseURL = (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? 'http://localhost:8000';

export const apiClient = axios.create({ baseURL });

apiClient.interceptors.request.use((config) => {
  const token = tokenStore.getAccessToken();
  if (token) {
    config.headers.set('Authorization', `Bearer ${token}`);
  }
  return config;
});

let refreshInFlight: Promise<string> | null = null;

async function performRefresh(): Promise<string> {
  const refreshToken = tokenStore.getRefreshToken();
  if (!refreshToken) {
    throw new Error('No refresh token available');
  }
  const response = await axios.post<ApiEnvelope<{ accessToken: string; refreshToken: string }>>(
    `${baseURL}/auth/refresh`,
    { refreshToken },
  );
  const { accessToken, refreshToken: rotatedRefreshToken } = response.data.data;
  tokenStore.setTokens(accessToken, rotatedRefreshToken);
  return accessToken;
}

let authFailureHandler: (() => void) | null = null;

/** Registered once by AuthContext so the interceptor can clear app state on an unrecoverable 401. */
export function registerAuthFailureHandler(handler: () => void): void {
  authFailureHandler = handler;
}

apiClient.interceptors.response.use(
  (response) => response,
  async (error: AxiosError<ApiErrorEnvelope>) => {
    const originalRequest = error.config as (InternalAxiosRequestConfig & { _retried?: boolean }) | undefined;
    const status = error.response?.status;
    const url = originalRequest?.url ?? '';
    const isAuthLifecycleCall = url.includes('/auth/login') || url.includes('/auth/refresh');

    if (status === 401 && originalRequest && !originalRequest._retried && !isAuthLifecycleCall) {
      originalRequest._retried = true;
      try {
        refreshInFlight = refreshInFlight ?? performRefresh();
        const newAccessToken = await refreshInFlight;
        refreshInFlight = null;
        originalRequest.headers.set('Authorization', `Bearer ${newAccessToken}`);
        return apiClient(originalRequest);
      } catch {
        refreshInFlight = null;
        tokenStore.clear();
        authFailureHandler?.();
        return Promise.reject(new ApiError('UNAUTHENTICATED', 'Your session has expired. Please log in again.'));
      }
    }

    const body = error.response?.data;
    if (body && !body.success) {
      return Promise.reject(
        new ApiError(body.error.code, body.error.message, body.error.details ?? [], body.requestId, status),
      );
    }
    return Promise.reject(
      new ApiError('NETWORK_ERROR', error.message || 'Network error — please check your connection.', [], undefined, status),
    );
  },
);

export async function unwrap<T>(promise: Promise<{ data: ApiEnvelope<T> }>): Promise<T> {
  const response = await promise;
  return response.data.data;
}

export async function unwrapPaginated<T>(
  promise: Promise<{ data: PaginatedEnvelope<T> }>,
): Promise<{ items: T[]; pagination: PaginationMeta }> {
  const response = await promise;
  return { items: response.data.data, pagination: response.data.pagination };
}
