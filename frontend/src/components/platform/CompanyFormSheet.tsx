import { useEffect } from 'react';
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
import { createCompany, updateCompany, type Company, type CompanyStatus } from '@/lib/api/company';
import { platformCompanyKeys } from '@/lib/queryKeys';

const COMPANY_STATUSES: CompanyStatus[] = ['trial', 'active', 'suspended'];

const companySchema = z.object({
  name: z.string().trim().min(1, 'Company name is required').max(255),
  status: z.enum(['trial', 'active', 'suspended']),
  currency: z.string().trim().max(10).optional(),
  gstNumber: z.string().trim().max(15).optional(),
});

type CompanyFormValues = z.infer<typeof companySchema>;

const EMPTY_VALUES: CompanyFormValues = { name: '', status: 'trial', currency: 'INR', gstNumber: '' };

export interface CompanyFormSheetProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  company?: Company;
  onSaved?: (company: Company) => void;
}

// Same Sheet drives both create and edit, mirroring LeadFormSheet/
// ClientFormSheet's exact pattern. Platform-admin-only — CompanyViewSet
// enforces this server-side regardless of what this form sends.
export function CompanyFormSheet({ open, onOpenChange, company, onSaved }: CompanyFormSheetProps) {
  const isEdit = !!company;
  const queryClient = useQueryClient();

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
    reset(
      company
        ? {
            name: company.name,
            status: company.status,
            currency: company.currency,
            gstNumber: company.gstNumber ?? '',
          }
        : EMPTY_VALUES,
    );
  }, [open, company, reset]);

  const mutation = useMutation({
    mutationFn: (values: CompanyFormValues) => {
      const input = {
        name: values.name,
        status: values.status,
        currency: values.currency || 'INR',
        gstNumber: values.gstNumber || null,
      };
      return isEdit ? updateCompany(company!.id, input) : createCompany(input);
    },
    onSuccess: (saved) => {
      queryClient.invalidateQueries({ queryKey: platformCompanyKeys.lists() });
      if (isEdit) queryClient.invalidateQueries({ queryKey: platformCompanyKeys.detail(saved.id) });
      toast.success(isEdit ? 'Company updated' : 'Company created');
      onOpenChange(false);
      onSaved?.(saved);
    },
    onError: (error: unknown) => {
      if (error instanceof ApiError && error.code === 'VALIDATION_ERROR') {
        for (const detail of error.details) {
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

  const onSubmit = (values: CompanyFormValues) => mutation.mutate(values);

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent className="overflow-y-auto">
        <SheetHeader>
          <SheetTitle>{isEdit ? 'Edit company' : 'New company'}</SheetTitle>
          <SheetDescription>
            {isEdit ? 'Update this tenant’s details.' : 'Create a new tenant company. It starts with no members — add its first Owner separately.'}
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
