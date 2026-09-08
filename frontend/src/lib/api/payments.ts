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
  notes: string;
  createdAt: string;
  updatedAt: string;
}

// `method` is a free-text field with no backend enum (confirmed in
// Payment's model docstring — "no documented value domain") — never
// render it as a fixed Select of invented options (Cash/UPI/etc).
export interface PaymentCreateInput {
  paymentDate: string;
  amount: string;
  method?: string;
  referenceNumber?: string;
  receiptUrl?: string;
  notes?: string;
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
