import { apiClient, unwrap, unwrapPaginated, type PaginationMeta } from './client';

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

// Full CompanyMembershipSerializer shape, for the Settings > Members admin
// table. `CompanyMembershipStatus` has exactly 3 values — there is no
// "suspended" literal, suspend/reactivate map to revoked/active.
export type MembershipStatus = 'active' | 'invited' | 'revoked';

export interface CompanyMembership {
  id: string;
  companyId: string;
  companyName: string;
  companyStatus: string;
  userId: string;
  userEmail: string;
  userName: string;
  roleId: string | null;
  roleName: string | null;
  status: MembershipStatus;
  createdAt: string;
  updatedAt: string;
}

export type MembershipOrdering = 'created_at' | '-created_at' | 'status' | '-status';

export interface MembershipListParams {
  status?: MembershipStatus;
  search?: string;
  ordering?: MembershipOrdering;
  page?: number;
  pageSize?: number;
}

export async function getCompanyMemberships(
  params: MembershipListParams,
): Promise<{ items: CompanyMembership[]; pagination: PaginationMeta }> {
  return unwrapPaginated<CompanyMembership>(
    apiClient.get('/company-memberships', {
      params: {
        status: params.status || undefined,
        search: params.search || undefined,
        ordering: params.ordering,
        page: params.page,
        pageSize: params.pageSize,
      },
    }),
  );
}

export async function getCompanyMembership(id: string): Promise<CompanyMembership> {
  return unwrap<CompanyMembership>(apiClient.get(`/company-memberships/${id}`));
}

// POST /company-memberships requires an EXISTING user identity — it invites
// an existing account into the company, it does not create a new user or
// send a signup link. roleId is required (no default-role concept exists).
export interface InviteMemberInput {
  email: string;
  roleId: string;
}

export async function inviteMember(input: InviteMemberInput): Promise<CompanyMembership> {
  return unwrap<CompanyMembership>(apiClient.post('/company-memberships', input));
}

// Soft-deletes the CompanyMembership row only — never the global User
// account. The same person keeps their login and any OTHER company's
// membership; they simply lose access to this one company.
export async function removeMember(id: string): Promise<void> {
  await apiClient.delete(`/company-memberships/${id}`);
}

export async function assignMemberRole(id: string, roleId: string | null): Promise<CompanyMembership> {
  return unwrap<CompanyMembership>(apiClient.post(`/company-memberships/${id}/assign-role`, { roleId }));
}

export async function suspendMember(id: string): Promise<CompanyMembership> {
  return unwrap<CompanyMembership>(apiClient.post(`/company-memberships/${id}/suspend`, {}));
}

export async function reactivateMember(id: string): Promise<CompanyMembership> {
  return unwrap<CompanyMembership>(apiClient.post(`/company-memberships/${id}/reactivate`, {}));
}
