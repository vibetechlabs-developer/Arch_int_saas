import { apiClient, unwrap, unwrapPaginated, type PaginationMeta } from './client';

// Mirrors backend/apps/projects/serializers.py::ProjectSerializer exactly.
// No `description` field exists on the backend model — not shown anywhere.
export interface Project {
  id: string;
  name: string;
  companyId: string;
  clientId: string;
  clientName: string;
  startDate: string | null;
  deadline: string | null;
  status: ProjectStatus;
  priority: string;
  assignedToId: string | null;
  assignedToName: string | null;
  followUpReminderAt: string | null;
  createdAt: string;
  updatedAt: string;
}

// The 11 documented ProjectStatus values (apps/projects/models.py).
export type ProjectStatus =
  | 'draft'
  | 'planning'
  | 'design'
  | 'quotation'
  | 'approved'
  | 'execution'
  | 'quality_check'
  | 'handover'
  | 'completed'
  | 'on_hold'
  | 'cancelled';

export const PROJECT_STATUSES: ProjectStatus[] = [
  'draft',
  'planning',
  'design',
  'quotation',
  'approved',
  'execution',
  'quality_check',
  'handover',
  'completed',
  'on_hold',
  'cancelled',
];

export type ProjectOrdering =
  | 'name'
  | '-name'
  | 'created_at'
  | '-created_at'
  | 'updated_at'
  | '-updated_at'
  | 'start_date'
  | '-start_date'
  | 'deadline'
  | '-deadline';

export interface ProjectListParams {
  status?: ProjectStatus;
  client?: string;
  assignedTo?: string;
  priority?: string;
  ordering?: ProjectOrdering;
  page?: number;
  pageSize?: number;
}

export interface ProjectMutableInput {
  name: string;
  startDate?: string | null;
  deadline?: string | null;
  priority?: string;
  assignedTo?: string | null;
  followUpReminderAt?: string | null;
}

export interface ProjectCreateInput extends ProjectMutableInput {
  clientId: string;
}

export interface ProjectMember {
  id: string;
  projectId: string;
  userId: string | null;
  userName: string | null;
  userEmail: string | null;
  assignedById: string | null;
  assignedByName: string | null;
  createdAt: string;
}

export async function getProjects(
  params: ProjectListParams,
): Promise<{ items: Project[]; pagination: PaginationMeta }> {
  return unwrapPaginated<Project>(
    apiClient.get('/projects', {
      params: {
        status: params.status || undefined,
        client: params.client || undefined,
        assignedTo: params.assignedTo || undefined,
        priority: params.priority || undefined,
        ordering: params.ordering,
        page: params.page,
        pageSize: params.pageSize,
      },
    }),
  );
}

export async function getProject(id: string): Promise<Project> {
  return unwrap<Project>(apiClient.get(`/projects/${id}`));
}

export async function createProject(input: ProjectCreateInput): Promise<Project> {
  return unwrap<Project>(apiClient.post('/projects', input));
}

export async function updateProject(id: string, input: Partial<ProjectMutableInput>): Promise<Project> {
  return unwrap<Project>(apiClient.patch(`/projects/${id}`, input));
}

export async function deleteProject(id: string): Promise<void> {
  await apiClient.delete(`/projects/${id}`);
}

export async function transitionProjectStatus(id: string, targetStatus: ProjectStatus): Promise<Project> {
  return unwrap<Project>(apiClient.patch(`/projects/${id}/status`, { status: targetStatus }));
}

export async function getProjectTeam(projectId: string): Promise<ProjectMember[]> {
  return unwrap<ProjectMember[]>(apiClient.get(`/projects/${projectId}/team`));
}

export async function addProjectTeamMember(projectId: string, userId: string): Promise<ProjectMember> {
  return unwrap<ProjectMember>(apiClient.post(`/projects/${projectId}/team`, { userId }));
}

export async function removeProjectTeamMember(projectId: string, userId: string): Promise<void> {
  await apiClient.delete(`/projects/${projectId}/team/${userId}`);
}
