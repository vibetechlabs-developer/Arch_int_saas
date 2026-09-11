import { apiClient, unwrap } from './client';

// Mirrors backend/apps/company/serializers.py::CompanySerializer. There is
// no "get current company" endpoint — the caller resolves companyId from
// GET /auth/memberships first, then fetches this by id.
export type CompanyStatus = 'trial' | 'active' | 'suspended';

export interface Company {
  id: string;
  name: string;
  status: CompanyStatus;
  currency: string;
  gstNumber: string | null;
  logoUrl: string;
  settings: Record<string, unknown>;
  createdAt: string;
  updatedAt: string;
}

// Mirrors CompanyUpdateSerializer. `status` is intentionally omitted here —
// the backend silently drops it for non-platform-admin callers (no error,
// just ignored), so exposing an editable status control here would be
// misleading UI for the only audience this page is built for.
export interface CompanyUpdateInput {
  name?: string;
  currency?: string;
  gstNumber?: string | null;
  logoUrl?: string;
  /** Internal-only (BE-078) — the `key` from uploadCompanyLogo's response, passed through so replacing/removing the logo cleans up the exact file. Omit for a manually-entered logoUrl, and omit both fields entirely when the logo wasn't touched. */
  logoStorageKey?: string;
}

// Mirrors backend/apps/company/serializers.py::CompanyLogoUploadSerializer.
export interface UploadedCompanyLogo {
  url: string;
  key: string;
  fileName: string;
  contentType: string;
  size: number;
}

export async function getCompany(id: string): Promise<Company> {
  return unwrap<Company>(apiClient.get(`/companies/${id}`));
}

export async function updateCompany(id: string, input: CompanyUpdateInput): Promise<Company> {
  return unwrap<Company>(apiClient.patch(`/companies/${id}`, input));
}

// Multipart upload — the browser/axios set the Content-Type boundary
// automatically from the FormData body; never set it manually. Returns an
// absolute URL + internal key that the caller then passes to
// updateCompany as logoUrl/logoStorageKey — this endpoint never touches
// Company itself (mirrors uploadProductImage's decoupled design).
export async function uploadCompanyLogo(companyId: string, file: File): Promise<UploadedCompanyLogo> {
  const formData = new FormData();
  formData.append('logo', file);
  return unwrap<UploadedCompanyLogo>(apiClient.post(`/companies/${companyId}/logo/upload`, formData));
}
