import { apiClient, unwrapPaginated } from './client';

// Mirrors backend/apps/users/serializers.py::CompanyMembershipSerializer —
// only the fields the Project team "add member" combobox needs.
export interface CompanyMemberOption {
  id: string;
  userId: string;
  userName: string;
  userEmail: string;
  roleName: string | null;
  status: string;
}

export async function searchActiveCompanyMembers(search: string): Promise<CompanyMemberOption[]> {
  const { items } = await unwrapPaginated<CompanyMemberOption>(
    apiClient.get('/company-memberships', { params: { search: search || undefined, status: 'active' } }),
  );
  return items;
}
