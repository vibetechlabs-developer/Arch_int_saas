import { apiClient, unwrap, unwrapPaginated, type PaginationMeta } from './client';

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

// Mirrors CompanyUpdateSerializer. `status` was originally omitted from
// this shared type — the backend silently drops it for non-platform-admin
// callers (no error, just ignored), so exposing an editable status control
// on the tenant-facing Company Settings page would be misleading UI for
// that audience. It's included now (optional) specifically for the
// platform console (pages/platform/*), the one caller that's actually a
// platform admin and can make it stick; CompanySettingsPage.tsx simply
// never sets it.
export interface CompanyUpdateInput {
  name?: string;
  status?: CompanyStatus;
  currency?: string;
  gstNumber?: string | null;
  logoUrl?: string;
  /** Internal-only (BE-078) — the `key` from uploadCompanyLogo's response, passed through so replacing/removing the logo cleans up the exact file. Omit for a manually-entered logoUrl, and omit both fields entirely when the logo wasn't touched. */
  logoStorageKey?: string;
}

// --- Platform-admin-only operations below --------------------------
// Backed by the same CompanyViewSet the tenant-facing functions above use
// (GET/PATCH already shared) — `list`/`create`/`destroy` are enforced
// server-side as platform-admin-exclusive
// (IsPlatformAdminOrCompanyAccess.has_permission denies any non-admin
// outright), so calling these from a company-user session would 403
// regardless of what this client sends.

export type CompanyOrdering = 'name' | '-name' | 'created_at' | '-created_at' | 'updated_at' | '-updated_at';

export interface CompanyListParams {
  status?: CompanyStatus;
  search?: string;
  ordering?: CompanyOrdering;
  page?: number;
}

// Mirrors CompanyCreateSerializer. `ownerEmail`/`ownerName` are optional
// on the backend (any other programmatic caller stays backward
// compatible) but the console's own CompanyFormSheet always sends both —
// creating a company with no owner just reproduces the original gap this
// form was built to close. When both are sent, the backend also grants
// that email the new company's Owner role via the same Add User flow
// (BE-071) used elsewhere — a new User with an unusable password plus an
// account-setup email, or an existing User linked if the email already
// has an account.
export interface CompanyCreateInput {
  name: string;
  status?: CompanyStatus;
  currency?: string;
  gstNumber?: string | null;
  ownerEmail?: string;
  ownerName?: string;
}

// The extra `owner` key CompanyViewSet.create() adds to its response only
// when ownerEmail/ownerName were supplied — absent (not merely null) on
// every other create call, matching the backend's own response shape.
export interface CompanyOwnerResult {
  userCreated: boolean;
  activationRequired: boolean;
}

export interface CreatedCompany extends Company {
  owner?: CompanyOwnerResult;
}

export async function getCompanies(params: CompanyListParams): Promise<{ items: Company[]; pagination: PaginationMeta }> {
  return unwrapPaginated<Company>(
    apiClient.get('/companies', {
      params: {
        status: params.status || undefined,
        search: params.search || undefined,
        ordering: params.ordering,
        page: params.page,
      },
    }),
  );
}

export async function createCompany(input: CompanyCreateInput): Promise<CreatedCompany> {
  return unwrap<CreatedCompany>(apiClient.post('/companies', input));
}

export async function deleteCompany(id: string): Promise<void> {
  await apiClient.delete(`/companies/${id}`);
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
