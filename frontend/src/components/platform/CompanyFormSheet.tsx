import { useEffect, useState } from 'react';
import { zodResolver } from '@hookform/resolvers/zod';
import { useForm } from 'react-hook-form';
import { z } from 'zod';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Alert } from '@/components/ui/alert';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetDescription } from '@/components/ui/sheet';
import { humanizeStatus } from '@/components/common/StatusBadge';
import { ApiError } from '@/lib/api/client';
import { createCompany, updateCompany, type Company, type CompanyStatus, type CreatedCompany } from '@/lib/api/company';
import { platformCompanyKeys } from '@/lib/queryKeys';

const COMPANY_STATUSES: CompanyStatus[] = ['trial', 'active', 'suspended'];

// ownerEmail/ownerName are optional at the schema/type level (the backend
// itself only requires them together, and updateCompany never sends
// either) — this form enforces "required in create mode" itself, via
// ownerError below, the same manual-check pattern ProjectFormSheet uses
// for its own create-only required field (clientId).
const companySchema = z.object({
  name: z.string().trim().min(1, 'Company name is required').max(255),
  status: z.enum(['trial', 'active', 'suspended']),
  currency: z.string().trim().max(10).optional(),
  gstNumber: z.string().trim().max(15).optional(),
  ownerEmail: z.string().trim().email('Enter a valid email address').optional().or(z.literal('')),
  ownerName: z.string().trim().max(255).optional(),
});

type CompanyFormValues = z.infer<typeof companySchema>;

const EMPTY_VALUES: CompanyFormValues = {
  name: '',
  status: 'trial',
  currency: 'INR',
  gstNumber: '',
  ownerEmail: '',
  ownerName: '',
};

export interface CompanyFormSheetProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  company?: Company;
  onSaved?: (company: Company) => void;
}

// Same Sheet drives both create and edit, mirroring LeadFormSheet/
// ClientFormSheet's exact pattern. Platform-admin-only — CompanyViewSet
// enforces this server-side regardless of what this form sends. The
// Owner fields only appear in create mode — an already-created company
// already has members, so "who's the Owner" isn't a field to edit here,
// it's Settings → Members' job.
export function CompanyFormSheet({ open, onOpenChange, company, onSaved }: CompanyFormSheetProps) {
  const isEdit = !!company;
  const queryClient = useQueryClient();
  const [ownerError, setOwnerError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    reset,
    setError,
    setValue,
    watch,
    formState: { errors, isSubmitting },
  } = useForm<CompanyFormValues>({ resolver: zodResolver(companySchema), defaultValues: EMPTY_VALUES });

  const status = watch('status');

  useEffect(() => {
    if (!open) return;
    setOwnerError(null);
    reset(
      company
        ? {
            name: company.name,
            status: company.status,
            currency: company.currency,
            gstNumber: company.gstNumber ?? '',
            ownerEmail: '',
            ownerName: '',
          }
        : EMPTY_VALUES,
    );
  }, [open, company, reset]);

  const mutation = useMutation({
    mutationFn: (values: CompanyFormValues) => {
      if (isEdit) {
        return updateCompany(company!.id, {
          name: values.name,
          status: values.status,
          currency: values.currency || 'INR',
          gstNumber: values.gstNumber || null,
        });
      }
      return createCompany({
        name: values.name,
        status: values.status,
        currency: values.currency || 'INR',
        gstNumber: values.gstNumber || null,
        ownerEmail: values.ownerEmail || undefined,
        ownerName: values.ownerName || undefined,
      });
    },
    onSuccess: (saved: Company | CreatedCompany) => {
      queryClient.invalidateQueries({ queryKey: platformCompanyKeys.lists() });
      if (isEdit) queryClient.invalidateQueries({ queryKey: platformCompanyKeys.detail(saved.id) });
      const owner = 'owner' in saved ? saved.owner : undefined;
      if (owner) {
        toast.success(
          owner.userCreated
            ? 'Company created — an account-setup email was sent to the new Owner'
            : 'Company created — the existing account was granted Owner access',
        );
      } else {
        toast.success(isEdit ? 'Company updated' : 'Company created');
      }
      onOpenChange(false);
      onSaved?.(saved);
    },
    onError: (error: unknown) => {
      if (error instanceof ApiError && error.code === 'VALIDATION_ERROR') {
        for (const detail of error.details) {
          if (detail.field === 'ownerEmail' || detail.field === 'ownerName') {
            setOwnerError(detail.issue);
            continue;
          }
          if (detail.field in EMPTY_VALUES) {
            setError(detail.field as keyof CompanyFormValues, { message: detail.issue });
          }
        }
        return;
      }
      const message = error instanceof ApiError ? error.message : 'Something went wrong. Please try again.';
      toast.error(message);
    },
  });

  const onSubmit = (values: CompanyFormValues) => {
    setOwnerError(null);
    if (!isEdit && (!values.ownerEmail || !values.ownerName)) {
      setOwnerError('Enter the new Owner’s name and email — every company needs at least one.');
      return;
    }
    mutation.mutate(values);
  };

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent className="overflow-y-auto">
        <SheetHeader>
          <SheetTitle>{isEdit ? 'Edit company' : 'New company'}</SheetTitle>
          <SheetDescription>
            {isEdit
              ? 'Update this tenant’s details.'
              : 'Create a new tenant company and grant its first Owner access in one step.'}
          </SheetDescription>
        </SheetHeader>

        <form onSubmit={handleSubmit(onSubmit)} className="flex flex-1 flex-col gap-5" noValidate>
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="company-name">Company name</Label>
            <Input id="company-name" invalid={!!errors.name} {...register('name')} />
            {errors.name && <p className="text-small text-danger-text">{errors.name.message}</p>}
          </div>

          <div className="flex flex-col gap-1.5">
            <Label>Status</Label>
            <Select value={status} onValueChange={(value) => setValue('status', value as CompanyStatus, { shouldDirty: true })}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {COMPANY_STATUSES.map((value) => (
                  <SelectItem key={value} value={value}>
                    {humanizeStatus(value)}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="company-currency">Currency</Label>
              <Input id="company-currency" placeholder="INR" invalid={!!errors.currency} {...register('currency')} />
              {errors.currency && <p className="text-small text-danger-text">{errors.currency.message}</p>}
            </div>
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="company-gstin">GSTIN</Label>
              <Input id="company-gstin" invalid={!!errors.gstNumber} {...register('gstNumber')} />
              {errors.gstNumber && <p className="text-small text-danger-text">{errors.gstNumber.message}</p>}
            </div>
          </div>

          {!isEdit && (
            <div className="flex flex-col gap-3 rounded-lg border border-border-subtle bg-surface-secondary p-4">
              <div className="flex flex-col gap-0.5">
                <span className="text-small font-medium text-text-primary">First Owner</span>
                <span className="text-caption text-text-tertiary">
                  Granted the Owner role immediately. A new email gets an account-setup message; an existing account
                  is simply added to this company.
                </span>
              </div>
              <div className="flex flex-col gap-1.5">
                <Label htmlFor="company-owner-name">Owner name</Label>
                <Input id="company-owner-name" invalid={!!errors.ownerName || !!ownerError} {...register('ownerName')} />
                {errors.ownerName && <p className="text-small text-danger-text">{errors.ownerName.message}</p>}
              </div>
              <div className="flex flex-col gap-1.5">
                <Label htmlFor="company-owner-email">Owner email</Label>
                <Input
                  id="company-owner-email"
                  type="email"
                  invalid={!!errors.ownerEmail || !!ownerError}
                  {...register('ownerEmail')}
                />
                {errors.ownerEmail && <p className="text-small text-danger-text">{errors.ownerEmail.message}</p>}
              </div>
              {ownerError && <p className="text-small text-danger-text">{ownerError}</p>}
            </div>
          )}

          {mutation.isError && !(mutation.error instanceof ApiError && mutation.error.code === 'VALIDATION_ERROR') && (
            <Alert variant="destructive">
              {mutation.error instanceof ApiError ? mutation.error.message : 'Something went wrong.'}
            </Alert>
          )}

          <div className="mt-auto flex justify-end gap-2 border-t border-border-subtle pt-4">
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)} disabled={isSubmitting}>
              Cancel
            </Button>
            <Button type="submit" variant="primary" loading={isSubmitting}>
              {isEdit ? 'Save changes' : 'Create company'}
            </Button>
          </div>
        </form>
      </SheetContent>
    </Sheet>
  );
}
