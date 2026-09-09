import { apiClient, unwrap } from './client';
import type { ProductUnit } from './products';

// Mirrors backend/apps/invoices/models.py::InvoiceStatus's 6 documented
// values. `overdue` is never persisted — InvoiceSerializer computes it at
// read time (sent/partially_paid + a past due date), so the API always
// reports the effective status directly; the frontend never re-derives it.
export type InvoiceStatus = 'draft' | 'sent' | 'partially_paid' | 'paid' | 'overdue' | 'cancelled';

// Mirrors InvoiceItemSerializer. No independent CRUD — items only ever
// change via a full-array PATCH on the parent invoice (draft only). No
// `productId`: unlike BOQItem/QuotationItem, an invoice line is always a
// frozen description/quantity/rate snapshot, never a catalog reference.
export interface InvoiceItem {
  id: string;
  description: string;
  quantity: string;
  unit: ProductUnit | '';
  rate: string;
  amount: string;
}

// Mirrors InvoiceSerializer. There is deliberately no `issueDate` field —
// only `createdAt`/`dueDate` exist. `paidAmount`/`outstandingAmount`
// (BE-074) are backend-authoritative decimal strings, read-only (never
// accepted by InvoiceUpdateInput below) — the frontend must never derive
// either from PaymentHistory or from `total` itself.
export interface Invoice {
  id: string;
  companyId: string;
  projectId: string;
  projectName: string;
  quotationId: string | null;
  clientId: string;
  clientName: string;
  invoiceNumber: string;
  subtotal: string;
  discount: string;
  tax: string;
  total: string;
  dueDate: string | null;
  paymentTerms: string;
  status: InvoiceStatus;
  paidAmount: string;
  outstandingAmount: string;
  notes: string;
  items: InvoiceItem[];
  createdAt: string;
  updatedAt: string;
}

export type InvoiceOrdering = 'created_at' | '-created_at' | 'due_date' | '-due_date' | 'updated_at' | '-updated_at';

export interface InvoiceItemInput {
  description: string;
  quantity: string;
  unit?: ProductUnit | '';
  rate: string;
}

// Exactly one of `quotationId`/`items` must be supplied — enforced
// server-side (400 otherwise), not encoded in this type, since both a
// quotation-derived and an ad hoc create call this same function with
// deliberately different fields populated.
export interface InvoiceCreateInput {
  quotationId?: string | null;
  items?: InvoiceItemInput[];
  discount?: string | null;
  tax?: string | null;
  dueDate?: string | null;
  paymentTerms?: string;
  notes?: string;
}

// Every field optional with no non-None default — an omitted field's
// absence (other than `items`) signals InvoiceService.update_invoice to
// leave it unchanged. Draft invoices only (409 otherwise).
export interface InvoiceUpdateInput {
  items?: InvoiceItemInput[];
  discount?: string | null;
  tax?: string | null;
  dueDate?: string | null;
  paymentTerms?: string | null;
  notes?: string | null;
}

export async function getInvoices(projectId: string, ordering?: InvoiceOrdering): Promise<Invoice[]> {
  return unwrap<Invoice[]>(apiClient.get(`/projects/${projectId}/invoices`, { params: { ordering } }));
}

export async function getInvoice(id: string): Promise<Invoice> {
  return unwrap<Invoice>(apiClient.get(`/invoices/${id}`));
}

export async function createInvoice(projectId: string, input: InvoiceCreateInput): Promise<Invoice> {
  return unwrap<Invoice>(apiClient.post(`/projects/${projectId}/invoices`, input));
}

export async function updateInvoice(id: string, input: InvoiceUpdateInput): Promise<Invoice> {
  return unwrap<Invoice>(apiClient.patch(`/invoices/${id}`, input));
}

export async function sendInvoice(id: string): Promise<Invoice> {
  return unwrap<Invoice>(apiClient.post(`/invoices/${id}/send`));
}

export async function cancelInvoice(id: string): Promise<Invoice> {
  return unwrap<Invoice>(apiClient.post(`/invoices/${id}/cancel`));
}
