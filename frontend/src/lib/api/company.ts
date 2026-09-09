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
}

export async function getCompany(id: string): Promise<Company> {
  return unwrap<Company>(apiClient.get(`/companies/${id}`));
}

export async function updateCompany(id: string, input: CompanyUpdateInput): Promise<Company> {
  return unwrap<Company>(apiClient.patch(`/companies/${id}`, input));
}
