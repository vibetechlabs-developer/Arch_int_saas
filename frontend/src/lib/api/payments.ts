import { apiClient, unwrap } from './client';

// Mirrors backend/apps/payments/serializers.py::PaymentSerializer. There
// is no status field at all — a payment is either active (returned by
// the list) or voided (soft-deleted, simply absent from it); no
// pending/confirmed workflow exists. Every field is immutable after
// create — there is no PATCH/PUT endpoint anywhere for Payment.
export interface Payment {
  id: string;
  companyId: string;
  invoiceId: string;
  clientId: string;
  projectId: string;
  paymentDate: string;
  amount: string;
  method: string;
  referenceNumber: string;
  receiptUrl: string;
  /** True when this receipt was uploaded via uploadPaymentReceipt (BE-078) — fetch it through GET /payments/{id}/receipt rather than receiptUrl (blank in that case). */
  hasStoredReceipt: boolean;
  notes: string;
  createdAt: string;
  updatedAt: string;
}

// `method` is a free-text field with no backend enum (confirmed in
// Payment's model docstring — "no documented value domain") — never
// render it as a fixed Select of invented options (Cash/UPI/etc).
// Exactly one of `receiptUrl` (legacy manual URL) / `receiptStorageKey`
// (from uploadPaymentReceipt, BE-078) may be supplied — never both.
// Payment has no update endpoint, so a receipt is only ever attached
// here, at creation.
export interface PaymentCreateInput {
  paymentDate: string;
  amount: string;
  method?: string;
  referenceNumber?: string;
  receiptUrl?: string;
  receiptStorageKey?: string;
  notes?: string;
}

// Mirrors backend/apps/payments/serializers.py::PaymentReceiptUploadSerializer.
export interface UploadedPaymentReceipt {
  key: string;
  fileName: string;
  contentType: string;
  size: number;
}

// GET /invoices/{id}/payments — unpaginated, no ordering param (backend
// applies its own fixed `-payment_date, -created_at` ordering).
export async function getPayments(invoiceId: string): Promise<Payment[]> {
  return unwrap<Payment[]>(apiClient.get(`/invoices/${invoiceId}/payments`));
}

export async function createPayment(invoiceId: string, input: PaymentCreateInput): Promise<Payment> {
  return unwrap<Payment>(apiClient.post(`/invoices/${invoiceId}/payments`, input));
}

// DELETE /payments/{id} — voids (soft-deletes) the payment; the response
// is a plain confirmation message, not an updated Payment.
export async function voidPayment(paymentId: string): Promise<void> {
  await apiClient.delete(`/payments/${paymentId}`);
}

// Multipart upload to private storage (BE-078) — returns a storage key
// (no URL) that the caller passes to createPayment as receiptStorageKey.
// Decoupled from any specific Payment on purpose: a receipt is always
// uploaded *before* the Payment it belongs to exists.
export async function uploadPaymentReceipt(file: File): Promise<UploadedPaymentReceipt> {
  const formData = new FormData();
  formData.append('file', file);
  return unwrap<UploadedPaymentReceipt>(apiClient.post('/payments/receipts/upload', formData));
}

/** The authenticated download endpoint for a payment receipt with `hasStoredReceipt: true` — use with previewPdf/downloadPdf from '@/lib/pdf'. */
export function paymentReceiptDownloadUrl(paymentId: string): string {
  return `/payments/${paymentId}/receipt`;
}
