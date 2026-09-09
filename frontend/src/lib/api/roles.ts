import { apiClient, unwrap, unwrapPaginated, type PaginationMeta } from './client';

// Mirrors backend/apps/users/serializers.py::RoleSerializer. There is no
// system/protected-role flag on the backend (confirmed — Role has only
// name/description/company/isActive) — edit/delete restrictions can't be
// derived, so this UI never invents any.
export interface Role {
  id: string;
  name: string;
  description: string;
  companyId: string;
  companyName: string;
  isActive: boolean;
  createdAt: string;
  updatedAt: string;
}

export type RoleOrdering = 'name' | '-name' | 'created_at' | '-created_at' | 'updated_at' | '-updated_at' | 'is_active' | '-is_active';

export interface RoleListParams {
  isActive?: boolean;
  search?: string;
  ordering?: RoleOrdering;
  page?: number;
  pageSize?: number;
}

export interface RoleMutableInput {
  name: string;
  description?: string;
  isActive?: boolean;
}

export async function getRoles(params: RoleListParams): Promise<{ items: Role[]; pagination: PaginationMeta }> {
  return unwrapPaginated<Role>(
    apiClient.get('/roles', {
      params: {
        isActive: params.isActive,
        search: params.search || undefined,
        ordering: params.ordering,
        page: params.page,
        pageSize: params.pageSize,
      },
    }),
  );
}

export async function getRole(id: string): Promise<Role> {
  return unwrap<Role>(apiClient.get(`/roles/${id}`));
}

export async function createRole(input: RoleMutableInput): Promise<Role> {
  return unwrap<Role>(apiClient.post('/roles', input));
}

export async function updateRole(id: string, input: Partial<RoleMutableInput>): Promise<Role> {
  return unwrap<Role>(apiClient.patch(`/roles/${id}`, input));
}

export async function deleteRole(id: string): Promise<void> {
  await apiClient.delete(`/roles/${id}`);
}

// PUT /roles/{id}/permissions is a full-replacement write — the caller
// must submit the complete desired set, not a delta. Always pair a write
// with a getRolePermissions() read first so the submitted set is built
// from the role's real persisted grants, never a blank/guessed baseline.
export async function assignRolePermissions(roleId: string, permissionCodes: string[]): Promise<Role> {
  return unwrap<Role>(apiClient.put(`/roles/${roleId}/permissions`, { permissionCodes }));
}

// GET /roles/{id}/permissions (BE-072) — this role's currently persisted
// grants, sourced from RolePermission on the backend, never reconstructed
// from role-name assumptions or default/seed data. Required before
// opening any "edit this role's permissions" UI, so existing grants can
// be pre-checked accurately instead of guessed.
export interface RolePermissions {
  roleId: string;
  permissionCodes: string[];
}

export async function getRolePermissions(roleId: string): Promise<RolePermissions> {
  return unwrap<RolePermissions>(apiClient.get(`/roles/${roleId}/permissions`));
}
