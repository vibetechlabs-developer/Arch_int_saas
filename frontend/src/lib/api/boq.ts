import { apiClient, unwrap } from './client';
import type { ProductUnit } from './products';

// Mirrors backend/apps/boq/serializers.py::BOQItemSerializer.
export interface BOQItem {
  id: string;
  sectionId: string;
  productId: string | null;
  productName: string | null;
  description: string;
  quantity: string;
  unit: ProductUnit | '';
  rate: string;
  discount: string;
  tax: string;
  amount: string;
  isOptional: boolean;
  isAlternative: boolean;
  notes: string;
  createdAt: string;
  updatedAt: string;
}

// Mirrors BOQSectionSerializer — includes each section's own items (the
// whole BOQ tree comes back from one GET, not separate paginated calls).
export interface BOQSection {
  id: string;
  boqId: string;
  name: string;
  sortOrder: number;
  items: BOQItem[];
  createdAt: string;
  updatedAt: string;
}

// Mirrors BOQSerializer.
export interface BOQ {
  id: string;
  projectId: string;
  status: string;
  sections: BOQSection[];
  createdAt: string;
  updatedAt: string;
}

// Mirrors BOQSummarySerializer — decimal strings, already excludes
// isOptional/isAlternative items server-side.
export interface BOQSummary {
  subtotal: string;
  discount: string;
  tax: string;
  total: string;
}

export interface BOQItemMutableInput {
  description?: string;
  quantity?: string;
  unit?: ProductUnit | '';
  rate?: string;
  discount?: string;
  tax?: string;
  isOptional?: boolean;
  isAlternative?: boolean;
  notes?: string;
}

export interface BOQItemCreateInput extends BOQItemMutableInput {
  productId?: string | null;
}

export async function getBOQ(projectId: string): Promise<BOQ> {
  return unwrap<BOQ>(apiClient.get(`/projects/${projectId}/boq`));
}

export async function getBOQSummary(projectId: string): Promise<BOQSummary> {
  return unwrap<BOQSummary>(apiClient.get(`/projects/${projectId}/boq/summary`));
}

export async function createBOQSection(projectId: string, name: string): Promise<BOQSection> {
  return unwrap<BOQSection>(apiClient.post(`/projects/${projectId}/boq/sections`, { name }));
}

export async function updateBOQSection(sectionId: string, name: string): Promise<BOQSection> {
  return unwrap<BOQSection>(apiClient.patch(`/boq-sections/${sectionId}`, { name }));
}

export async function deleteBOQSection(sectionId: string): Promise<void> {
  await apiClient.delete(`/boq-sections/${sectionId}`);
}

export async function createBOQItem(
  projectId: string,
  sectionId: string,
  input: BOQItemCreateInput,
): Promise<BOQItem> {
  return unwrap<BOQItem>(apiClient.post(`/projects/${projectId}/boq/sections/${sectionId}/items`, input));
}

export async function updateBOQItem(itemId: string, input: BOQItemMutableInput): Promise<BOQItem> {
  return unwrap<BOQItem>(apiClient.patch(`/boq-items/${itemId}`, input));
}

export async function deleteBOQItem(itemId: string): Promise<void> {
  await apiClient.delete(`/boq-items/${itemId}`);
}
