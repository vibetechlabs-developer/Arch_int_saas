import { apiClient, unwrap } from './client';

// Mirrors backend/apps/users/serializers.py::PermissionSerializer.
// GET /permissions returns a flat, non-paginated array (a bare
// IsAuthenticated read-only reference catalog, not a business resource) —
// group by `module` client-side for a readable catalog UI.
export interface Permission {
  id: string;
  code: string;
  module: string;
  action: string;
  description: string;
  createdAt: string;
}

export async function getPermissions(): Promise<Permission[]> {
  return unwrap<Permission[]>(apiClient.get('/permissions'));
}

export function groupPermissionsByModule(permissions: Permission[]): { module: string; permissions: Permission[] }[] {
  const groups = new Map<string, Permission[]>();
  for (const permission of permissions) {
    const list = groups.get(permission.module) ?? [];
    list.push(permission);
    groups.set(permission.module, list);
  }
  return Array.from(groups.entries())
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([module, perms]) => ({ module, permissions: perms }));
}
