import { apiClient, unwrap } from './client';
import type { ProductUnit } from './products';

// Mirrors backend/apps/quotations/models.py::QuotationStatus's 6
// documented values. Only draft/sent/approved/rejected are ever actually
// reachable through the API — internal_review and revision_requested are
// enum values with no transition endpoint that sets them, but are kept
// here for completeness since a real Quotation row could carry either.
export type QuotationStatus = 'draft' | 'internal_review' | 'sent' | 'revision_requested' | 'approved' | 'rejected';

// Mirrors backend/apps/quotations/serializers.py::QuotationItemSerializer.
// No independent CRUD endpoint exists for this — it is always a nested,
// read-only snapshot line within a Quotation.
export interface QuotationItem {
  id: string;
  productId: string | null;
  productName: string | null;
  description: string;
  quantity: string;
  unit: ProductUnit | '';
  rate: string;
  amount: string;
}

// Mirrors QuotationSerializer. Every field here is server-computed or
// server-derived — there is no PATCH/DELETE endpoint for Quotation at
// all; content only ever changes via a new version (POST .../revise).
export interface Quotation {
  id: string;
  companyId: string;
  projectId: string;
  projectName: string;
  boqId: string | null;
  clientId: string;
  clientName: string;
  quoteNumber: string;
  version: number;
  subtotal: string;
  discount: string;
  tax: string;
  total: string;
  terms: string;
  paymentSchedule: unknown[];
  validUntil: string | null;
  status: QuotationStatus;
  notes: string;
  items: QuotationItem[];
  createdAt: string;
  updatedAt: string;
}

export type QuotationOrdering = 'created_at' | '-created_at' | 'version' | '-version' | 'updated_at' | '-updated_at';

export interface QuotationItemInput {
  productId?: string | null;
  description?: string;
  quantity: string;
  unit?: ProductUnit | '';
  rate?: string | null;
}

// `items` is deliberately optional with no default — omitting the key
// entirely (not sending an empty array) is what signals the backend to
// build the quotation from the project's current BOQ. This module only
// ever calls create/revise without an `items` key (the BOQ-derived flow,
// the one the backend documents as primary); manual line-item entry is a
// separate, larger feature not built in this pass.
export interface QuotationCreateInput {
  items?: QuotationItemInput[];
  discount?: string | null;
  tax?: string | null;
  terms?: string;
  paymentSchedule?: unknown[];
  validUntil?: string | null;
  notes?: string;
}

export interface QuotationReviseInput {
  items?: QuotationItemInput[];
  discount?: string | null;
  tax?: string | null;
  terms?: string | null;
  paymentSchedule?: unknown[] | null;
  validUntil?: string | null;
  notes?: string | null;
}

// Unpaginated — Finance_API.md documents this as "all versions" of every
// quotation for the project, a naturally small list, matching the same
// pattern as GET /projects/{id}/team.
export async function getQuotations(projectId: string, ordering?: QuotationOrdering): Promise<Quotation[]> {
  return unwrap<Quotation[]>(apiClient.get(`/projects/${projectId}/quotations`, { params: { ordering } }));
}

export async function getQuotation(id: string): Promise<Quotation> {
  return unwrap<Quotation>(apiClient.get(`/quotations/${id}`));
}

export async function createQuotation(projectId: string, input: QuotationCreateInput): Promise<Quotation> {
  return unwrap<Quotation>(apiClient.post(`/projects/${projectId}/quotations`, input));
}

export async function reviseQuotation(quotationId: string, input: QuotationReviseInput): Promise<Quotation> {
  return unwrap<Quotation>(apiClient.post(`/quotations/${quotationId}/revise`, input));
}

export async function sendQuotation(quotationId: string): Promise<Quotation> {
  return unwrap<Quotation>(apiClient.post(`/quotations/${quotationId}/send`));
}

export async function approveQuotation(quotationId: string): Promise<Quotation> {
  return unwrap<Quotation>(apiClient.post(`/quotations/${quotationId}/approve`));
}

export async function rejectQuotation(quotationId: string): Promise<Quotation> {
  return unwrap<Quotation>(apiClient.post(`/quotations/${quotationId}/reject`));
}
