import { apiClient, unwrap, unwrapPaginated, type PaginationMeta } from './client';

// Mirrors backend/apps/site_visits/serializers.py::SiteVisitSerializer exactly.
export interface SiteVisit {
  id: string;
  leadId: string | null;
  leadName: string | null;
  projectId: string | null;
  projectName: string | null;
  clientId: string | null;
  clientName: string | null;
  visitDate: string;
  assignedToId: string | null;
  assignedToName: string | null;
  address: string;
  measurements: string;
  requirements: string;
  photoUrls: string[];
  videoUrls: string[];
  notes: string;
  budget: string | null;
  siteConditions: string;
  followUpActions: string;
  reportSubmittedAt: string | null;
  isCompleted: boolean;
  companyId: string;
  createdAt: string;
  updatedAt: string;
}

export type SiteVisitOrdering = 'visit_date' | '-visit_date' | 'created_at' | '-created_at' | 'updated_at' | '-updated_at';

export interface SiteVisitListParams {
  lead?: string;
  project?: string;
  assignedTo?: string;
  ordering?: SiteVisitOrdering;
  page?: number;
}

export interface SiteVisitInput {
  leadId?: string | null;
  projectId?: string | null;
  visitDate: string;
  assignedToId?: string | null;
  address?: string;
  measurements?: string;
  requirements?: string;
  photoUrls?: string[];
  videoUrls?: string[];
  notes?: string;
  budget?: string | null;
  siteConditions?: string;
  followUpActions?: string;
}

export async function getSiteVisits(
  params: SiteVisitListParams,
): Promise<{ items: SiteVisit[]; pagination: PaginationMeta }> {
  return unwrapPaginated<SiteVisit>(
    apiClient.get('/site-visits', {
      params: {
        lead: params.lead || undefined,
        project: params.project || undefined,
        assignedTo: params.assignedTo || undefined,
        ordering: params.ordering,
        page: params.page,
      },
    }),
  );
}

export async function getSiteVisit(id: string): Promise<SiteVisit> {
  return unwrap<SiteVisit>(apiClient.get(`/site-visits/${id}`));
}

export async function createSiteVisit(input: SiteVisitInput): Promise<SiteVisit> {
  return unwrap<SiteVisit>(apiClient.post('/site-visits', input));
}

export async function updateSiteVisit(id: string, input: Partial<SiteVisitInput>): Promise<SiteVisit> {
  return unwrap<SiteVisit>(apiClient.patch(`/site-visits/${id}`, input));
}

export async function deleteSiteVisit(id: string): Promise<void> {
  await apiClient.delete(`/site-visits/${id}`);
}

export async function submitSiteVisitReport(
  id: string,
  input: { createProject?: boolean; projectName?: string } = {},
): Promise<SiteVisit> {
  return unwrap<SiteVisit>(apiClient.post(`/site-visits/${id}/report`, input));
}
