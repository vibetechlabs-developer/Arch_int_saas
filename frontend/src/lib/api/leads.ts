import { apiClient, unwrap, unwrapPaginated, type PaginationMeta } from './client';

// Mirrors backend/apps/leads/serializers.py::LeadSerializer exactly.
export interface Lead {
  id: string;
  name: string;
  companyName: string;
  email: string;
  mobile: string;
  source: string;
  status: LeadStatus;
  assignedToId: string | null;
  assignedToName: string | null;
  lossReason: string;
  followUpReminderAt: string | null;
  notes: string;
  convertedClientId: string | null;
  convertedClientName: string | null;
  convertedProjectId: string | null;
  convertedProjectName: string | null;
  companyId: string;
  createdAt: string;
  updatedAt: string;
}

// The 6 documented LeadStatus values (apps/leads/models.py).
export type LeadStatus = 'new' | 'qualified' | 'follow_up' | 'site_visit_scheduled' | 'won' | 'lost';

export const LEAD_STATUSES: LeadStatus[] = [
  'new',
  'qualified',
  'follow_up',
  'site_visit_scheduled',
  'won',
  'lost',
];

// `won` is never reachable via PATCH /leads/{id}/status — only via
// POST /leads/{id}/convert (apps/leads/models.py::TERMINAL_LEAD_STATUSES'
// docstring). Offering it in a plain status dropdown would just be an
// option that always 409s, so it's excluded from the selectable set.
export const LEAD_STATUS_TRANSITION_OPTIONS: LeadStatus[] = LEAD_STATUSES.filter((status) => status !== 'won');

export type LeadOrdering = 'name' | '-name' | 'created_at' | '-created_at' | 'updated_at' | '-updated_at' | 'status' | '-status';

export interface LeadListParams {
  status?: LeadStatus;
  assignedTo?: string;
  search?: string;
  ordering?: LeadOrdering;
  page?: number;
}

export interface LeadInput {
  name: string;
  companyName?: string;
  email?: string;
  mobile?: string;
  source?: string;
  assignedToId?: string | null;
  followUpReminderAt?: string | null;
  notes?: string;
}

export async function getLeads(params: LeadListParams): Promise<{ items: Lead[]; pagination: PaginationMeta }> {
  return unwrapPaginated<Lead>(
    apiClient.get('/leads', {
      params: {
        status: params.status || undefined,
        assignedTo: params.assignedTo || undefined,
        search: params.search || undefined,
        ordering: params.ordering,
        page: params.page,
      },
    }),
  );
}

export async function getLead(id: string): Promise<Lead> {
  return unwrap<Lead>(apiClient.get(`/leads/${id}`));
}

export async function createLead(input: LeadInput): Promise<Lead> {
  return unwrap<Lead>(apiClient.post('/leads', input));
}

export async function updateLead(id: string, input: Partial<LeadInput>): Promise<Lead> {
  return unwrap<Lead>(apiClient.patch(`/leads/${id}`, input));
}

export async function deleteLead(id: string): Promise<void> {
  await apiClient.delete(`/leads/${id}`);
}

export async function transitionLeadStatus(id: string, targetStatus: LeadStatus): Promise<Lead> {
  return unwrap<Lead>(apiClient.patch(`/leads/${id}/status`, { status: targetStatus }));
}

export async function markLeadLost(
  id: string,
  input: { lossReason: string; followUpReminderAt?: string | null },
): Promise<Lead> {
  return unwrap<Lead>(apiClient.post(`/leads/${id}/mark-lost`, input));
}

export async function convertLead(
  id: string,
  input: { createProject?: boolean; projectName?: string } = {},
): Promise<Lead> {
  return unwrap<Lead>(apiClient.post(`/leads/${id}/convert`, input));
}
