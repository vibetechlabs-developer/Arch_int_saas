import { useEffect, useState } from 'react';
import { zodResolver } from '@hookform/resolvers/zod';
import { useForm } from 'react-hook-form';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { toast } from 'sonner';
import { FileText } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Alert } from '@/components/ui/alert';
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetDescription } from '@/components/ui/sheet';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';
import { EmptyState } from '@/components/common/EmptyState';
import { FinancialSummary } from '@/components/common/FinancialSummary';
import { ApiError } from '@/lib/api/client';
import { getQuotations, type Quotation } from '@/lib/api/quotations';
import { createInvoice } from '@/lib/api/invoices';
import type { ProductUnit } from '@/lib/api/products';
import { invoiceKeys, quotationKeys } from '@/lib/queryKeys';
import {
  InvoiceLineItemFields,
  invoiceLineFormSchema,
  EMPTY_INVOICE_LINE_VALUES,
  type InvoiceLineFormValues,
} from './InvoiceLineItemFields';

export interface CreateInvoiceSheetProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  projectId: string;
}

// Only the latest version of an approved quote number is offered — an
// older, superseded version can still carry a stale "approved" status
// (revising resets the new version to draft, but never touches the old
// row), so filtering to the latest avoids invoicing a quote the project
// has since moved on from. This uses only data already returned by the
// API (status + version), not an invented business rule.
function latestApprovedQuotations(quotations: Quotation[]): Quotation[] {
  const latestByNumber = new Map<string, Quotation>();
  for (const q of quotations) {
    const existing = latestByNumber.get(q.quoteNumber);
    if (!existing || q.version > existing.version) latestByNumber.set(q.quoteNumber, q);
  }
  return Array.from(latestByNumber.values()).filter((q) => q.status === 'approved');
}

export function CreateInvoiceSheet({ open, onOpenChange, projectId }: CreateInvoiceSheetProps) {
  const [mode, setMode] = useState<'quotation' | 'manual'>('quotation');

  const { data: quotations, isLoading: quotationsLoading } = useQuery({
    queryKey: quotationKeys.project(projectId),
    queryFn: () => getQuotations(projectId),
    enabled: open,
  });

  useEffect(() => {
    if (open) setMode('quotation');
  }, [open]);

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent className="overflow-y-auto sm:max-w-lg">
        <SheetHeader>
          <SheetTitle>Create invoice</SheetTitle>
          <SheetDescription>Bill this project from an approved quotation, or enter charges manually.</SheetDescription>
        </SheetHeader>

        <Tabs value={mode} onValueChange={(v) => setMode(v as typeof mode)}>
          <TabsList>
            <TabsTrigger value="quotation">From Quotation</TabsTrigger>
            <TabsTrigger value="manual">Manual</TabsTrigger>
          </TabsList>
          <TabsContent value="quotation">
            <QuotationInvoiceForm
              projectId={projectId}
              quotations={latestApprovedQuotations(quotations ?? [])}
              loading={quotationsLoading}
              onOpenChange={onOpenChange}
            />
          </TabsContent>
          <TabsContent value="manual">
            <ManualInvoiceForm projectId={projectId} onOpenChange={onOpenChange} />
          </TabsContent>
        </Tabs>
      </SheetContent>
    </Sheet>
  );
}

interface QuotationFormValues {
  dueDate: string;
  paymentTerms: string;
  notes: string;
}

const EMPTY_QUOTATION_VALUES: QuotationFormValues = { dueDate: '', paymentTerms: '', notes: '' };

function QuotationInvoiceForm({
  projectId,
  quotations,
  loading,
  onOpenChange,
}: {
  projectId: string;
  quotations: Quotation[];
  loading: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [selectionError, setSelectionError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    formState: { isSubmitting },
  } = useForm<QuotationFormValues>({ defaultValues: EMPTY_QUOTATION_VALUES });

  const selected = quotations.find((q) => q.id === selectedId) ?? null;

  const mutation = useMutation({
    mutationFn: (values: QuotationFormValues) =>
      createInvoice(projectId, {
        quotationId: selectedId,
        dueDate: values.dueDate || null,
        paymentTerms: values.paymentTerms,
        notes: values.notes,
      }),
    onSuccess: (invoice) => {
      queryClient.invalidateQueries({ queryKey: invoiceKeys.project(projectId) });
      toast.success(`${invoice.invoiceNumber} created`);
      onOpenChange(false);
      navigate(`/invoices/${invoice.id}`);
    },
    onError: (error: unknown) => {
      toast.error(error instanceof ApiError ? error.message : 'Something went wrong. Please try again.');
    },
  });

  const onSubmit = (values: QuotationFormValues) => {
    if (!selectedId) {
      setSelectionError('Select a quotation to continue.');
      return;
    }
    setSelectionError(null);
    mutation.mutate(values);
  };

  if (!loading && quotations.length === 0) {
    return (
      <EmptyState
        icon={FileText}
        title="No approved quotations"
        description="Approve a quotation for this project before invoicing from it, or switch to Manual."
      />
    );
  }

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="flex flex-1 flex-col gap-5" noValidate>
      <div className="flex flex-col gap-1.5">
        <Label>Quotation</Label>
        <div className="flex flex-col gap-2" role="radiogroup" aria-label="Quotation">
          {loading
            ? Array.from({ length: 2 }).map((_, i) => (
                <div key={i} className="h-16 animate-pulse rounded-lg border border-border-subtle bg-surface-secondary" />
              ))
            : quotations.map((q) => (
                <button
                  key={q.id}
                  type="button"
                  role="radio"
                  aria-checked={selectedId === q.id}
                  onClick={() => {
                    setSelectedId(q.id);
                    setSelectionError(null);
                  }}
                  className={`flex items-center justify-between rounded-lg border p-3 text-left transition-colors duration-fast ${
                    selectedId === q.id ? 'border-accent-500 bg-accent-50' : 'border-border-subtle hover:bg-hover'
                  }`}
                >
                  <div className="flex flex-col">
                    <span className="text-body font-medium text-text-primary">
                      {q.quoteNumber} · v{q.version}
                    </span>
                    <span className="text-caption text-text-tertiary">{q.clientName}</span>
                  </div>
                  <span className="tabular-nums text-body text-text-primary">{q.total}</span>
                </button>
              ))}
        </div>
        {selectionError && <p className="text-small text-danger-text">{selectionError}</p>}
      </div>

      {selected && (
        <div className="flex flex-col gap-1.5 rounded-md border border-border-subtle bg-surface-secondary p-3">
          <span className="text-caption text-text-tertiary">This invoice will use the quotation's totals</span>
          <FinancialSummary subtotal={selected.subtotal} discount={selected.discount} tax={selected.tax} total={selected.total} />
        </div>
      )}

      <div className="flex flex-col gap-1.5">
        <Label htmlFor="invoice-quotation-due-date">Due date</Label>
        <Input id="invoice-quotation-due-date" type="date" {...register('dueDate')} />
      </div>

      <div className="flex flex-col gap-1.5">
        <Label htmlFor="invoice-quotation-payment-terms">Payment terms</Label>
        <Textarea id="invoice-quotation-payment-terms" rows={2} {...register('paymentTerms')} />
      </div>

      <div className="flex flex-col gap-1.5">
        <Label htmlFor="invoice-quotation-notes">Notes</Label>
        <Textarea id="invoice-quotation-notes" rows={2} {...register('notes')} />
      </div>

      {mutation.isError && (
        <Alert variant="destructive">{mutation.error instanceof ApiError ? mutation.error.message : 'Something went wrong.'}</Alert>
      )}

      <div className="mt-auto flex justify-end gap-2 border-t border-border-subtle pt-4">
        <Button type="button" variant="outline" onClick={() => onOpenChange(false)} disabled={isSubmitting}>
          Cancel
        </Button>
        <Button type="submit" variant="primary" loading={isSubmitting}>
          Create invoice
        </Button>
      </div>
    </form>
  );
}

function ManualInvoiceForm({ projectId, onOpenChange }: { projectId: string; onOpenChange: (open: boolean) => void }) {
  const queryClient = useQueryClient();
  const navigate = useNavigate();

  const {
    control,
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<InvoiceLineFormValues>({
    resolver: zodResolver(invoiceLineFormSchema),
    defaultValues: EMPTY_INVOICE_LINE_VALUES,
  });

  const mutation = useMutation({
    mutationFn: (values: InvoiceLineFormValues) =>
      createInvoice(projectId, {
        items: values.items.map((item) => ({
          description: item.description,
          quantity: item.quantity,
          unit: (item.unit || undefined) as ProductUnit | undefined,
          rate: item.rate,
        })),
        discount: values.discount || null,
        tax: values.tax || null,
        dueDate: values.dueDate || null,
        paymentTerms: values.paymentTerms,
        notes: values.notes,
      }),
    onSuccess: (invoice) => {
      queryClient.invalidateQueries({ queryKey: invoiceKeys.project(projectId) });
      toast.success(`${invoice.invoiceNumber} created`);
      onOpenChange(false);
      navigate(`/invoices/${invoice.id}`);
    },
    onError: (error: unknown) => {
      toast.error(error instanceof ApiError ? error.message : 'Something went wrong. Please try again.');
    },
  });

  return (
    <form onSubmit={handleSubmit((values) => mutation.mutate(values))} className="flex flex-1 flex-col gap-5" noValidate>
      <InvoiceLineItemFields control={control} register={register} errors={errors} />

      {mutation.isError && (
        <Alert variant="destructive">{mutation.error instanceof ApiError ? mutation.error.message : 'Something went wrong.'}</Alert>
      )}

      <div className="mt-auto flex justify-end gap-2 border-t border-border-subtle pt-4">
        <Button type="button" variant="outline" onClick={() => onOpenChange(false)} disabled={isSubmitting}>
          Cancel
        </Button>
        <Button type="submit" variant="primary" loading={isSubmitting}>
          Create invoice
        </Button>
      </div>
    </form>
  );
}
