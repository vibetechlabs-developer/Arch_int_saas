import { useEffect, useState } from 'react';
import { zodResolver } from '@hookform/resolvers/zod';
import { useForm } from 'react-hook-form';
import { z } from 'zod';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { Building2, ImageIcon } from 'lucide-react';
import { PageHeader } from '@/components/common/PageHeader';
import { ErrorState } from '@/components/common/ErrorState';
import { RestrictedState } from '@/components/common/RestrictedState';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { ProductImagePicker, validateProductImageFile } from '@/components/products/ProductImagePicker';
import { ApiError } from '@/lib/api/client';
import { getCompany, updateCompany, uploadCompanyLogo } from '@/lib/api/company';
import { companyKeys } from '@/lib/queryKeys';
import { useCurrentCompanyId } from '@/hooks/useCurrentCompanyId';

const schema = z.object({
  name: z.string().trim().min(1, 'Company name is required').max(255),
  currency: z.string().trim().min(1, 'Currency code is required').max(10),
  gstNumber: z.string().trim().max(15, 'GSTIN must be 15 characters or fewer').optional(),
});
type FormValues = z.infer<typeof schema>;

// Company.status is intentionally not an editable field here — the backend
// silently ignores a non-platform-admin's status change rather than
// erroring, so exposing a control that appears to work but doesn't would
// be misleading. It's shown read-only instead.
export default function CompanySettingsPage() {
  const { companyId, isLoading: isResolvingCompany, isError: membershipError, error: membershipErrorObj } =
    useCurrentCompanyId();
  const queryClient = useQueryClient();

  const { data: company, isLoading, isError, error, refetch } = useQuery({
    queryKey: companyId ? companyKeys.detail(companyId) : ['company', 'unresolved'],
    queryFn: () => getCompany(companyId!),
    enabled: !!companyId,
  });

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isDirty },
  } = useForm<FormValues>({ resolver: zodResolver(schema), defaultValues: { name: '', currency: '', gstNumber: '' } });

  useEffect(() => {
    if (company) {
      reset({ name: company.name, currency: company.currency, gstNumber: company.gstNumber ?? '' });
    }
  }, [company, reset]);

  const mutation = useMutation({
    mutationFn: (values: FormValues) =>
      updateCompany(companyId!, {
        name: values.name,
        currency: values.currency,
        gstNumber: values.gstNumber || null,
      }),
    onSuccess: (updated) => {
      queryClient.setQueryData(companyKeys.detail(companyId!), updated);
      toast.success('Company details saved');
    },
    onError: (mutationError: unknown) => {
      toast.error(mutationError instanceof ApiError ? mutationError.message : 'Failed to save company details.');
    },
  });

  // Logo upload/remove are instant actions (Upload / Replace / Remove),
  // independent of the profile form's Save button above — matches how a
  // logo is typically managed in real settings pages, and mirrors
  // ProductFormSheet's own two-step upload-then-attach pattern (BE-078).
  const [logoUrlDraft, setLogoUrlDraft] = useState<string | null>(null);
  const [logoError, setLogoError] = useState<string | null>(null);

  const logoUploadMutation = useMutation({
    mutationFn: async (file: File) => {
      const uploaded = await uploadCompanyLogo(companyId!, file);
      return updateCompany(companyId!, { logoUrl: uploaded.url, logoStorageKey: uploaded.key });
    },
    onSuccess: (updated) => {
      queryClient.setQueryData(companyKeys.detail(companyId!), updated);
      setLogoError(null);
      toast.success('Company logo updated');
    },
    onError: (mutationError: unknown) => {
      const message = mutationError instanceof ApiError ? mutationError.message : 'Failed to upload logo. Please try again.';
      setLogoError(message);
    },
  });

  const logoUrlMutation = useMutation({
    mutationFn: (logoUrl: string) => updateCompany(companyId!, { logoUrl }),
    onSuccess: (updated) => {
      queryClient.setQueryData(companyKeys.detail(companyId!), updated);
      setLogoUrlDraft(null);
      setLogoError(null);
      toast.success(updated.logoUrl ? 'Company logo updated' : 'Company logo removed');
    },
    onError: (mutationError: unknown) => {
      const message = mutationError instanceof ApiError ? mutationError.message : 'Failed to save logo. Please try again.';
      setLogoError(message);
    },
  });

  const logoBusy = logoUploadMutation.isPending || logoUrlMutation.isPending;

  const handleLogoFileSelect = (file: File) => {
    const validationMessage = validateProductImageFile(file);
    if (validationMessage) {
      setLogoError(validationMessage);
      return;
    }
    setLogoError(null);
    logoUploadMutation.mutate(file);
  };

  if (membershipError || isError) {
    const err = isError ? error : membershipErrorObj;
    if (err instanceof ApiError && err.status === 403) {
      return <RestrictedState message={err.message} />;
    }
    return <ErrorState error={err} onRetry={() => refetch()} />;
  }

  const loading = isResolvingCompany || isLoading || !company;

  return (
    <div className="flex flex-col gap-6">
      <PageHeader title="Company" description="Your organization's profile, currency, and tax details." />

      <Card>
        <CardHeader>
          <CardTitle>
            <Building2 className="size-4 text-text-tertiary" />
            Company profile
          </CardTitle>
          <CardDescription>Visible across quotations, invoices, and reports.</CardDescription>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="flex flex-col gap-4">
              <Skeleton className="h-9 w-full" />
              <Skeleton className="h-9 w-40" />
              <Skeleton className="h-9 w-56" />
            </div>
          ) : (
            <form
              onSubmit={handleSubmit((values) => mutation.mutate(values))}
              className="flex flex-col gap-5"
              noValidate
            >
              <div className="flex items-center gap-2">
                <span className="text-small text-text-tertiary">Status</span>
                <Badge variant={company.status === 'active' ? 'success' : company.status === 'suspended' ? 'danger' : 'neutral'}>
                  {company.status}
                </Badge>
              </div>

              <div className="flex flex-col gap-1.5">
                <Label htmlFor="company-name">Company name</Label>
                <Input id="company-name" invalid={!!errors.name} {...register('name')} />
                {errors.name && <p className="text-small text-danger-text">{errors.name.message}</p>}
              </div>

              <div className="grid gap-5 sm:grid-cols-2">
                <div className="flex flex-col gap-1.5">
                  <Label htmlFor="company-currency">Currency code</Label>
                  <Input id="company-currency" placeholder="INR" invalid={!!errors.currency} {...register('currency')} />
                  {errors.currency && <p className="text-small text-danger-text">{errors.currency.message}</p>}
                </div>
                <div className="flex flex-col gap-1.5">
                  <Label htmlFor="company-gst">GSTIN</Label>
                  <Input id="company-gst" placeholder="Optional" invalid={!!errors.gstNumber} {...register('gstNumber')} />
                  {errors.gstNumber && <p className="text-small text-danger-text">{errors.gstNumber.message}</p>}
                </div>
              </div>

              <div className="flex items-center justify-between border-t border-border-subtle pt-4">
                <p className="text-small text-text-tertiary">
                  {isDirty ? 'You have unsaved changes.' : 'All changes saved.'}
                </p>
                <Button type="submit" variant="primary" loading={mutation.isPending} disabled={!isDirty}>
                  Save changes
                </Button>
              </div>
            </form>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>
            <ImageIcon className="size-4 text-text-tertiary" />
            Company logo
          </CardTitle>
          <CardDescription>Used across the app shell and on BOQ/Quotation/Invoice PDF exports.</CardDescription>
        </CardHeader>
        <CardContent>
          {loading ? (
            <Skeleton className="h-32 w-32" />
          ) : (
            <ProductImagePicker
              label="Company logo"
              previewAlt="Company logo preview"
              currentUrl={logoUrlDraft ?? company.logoUrl}
              pendingFile={null}
              onFileSelect={handleLogoFileSelect}
              onRemove={() => logoUrlMutation.mutate('')}
              onUrlChange={setLogoUrlDraft}
              error={logoError}
              uploading={logoBusy}
              disabled={logoBusy}
            />
          )}
          {logoUrlDraft !== null && logoUrlDraft !== company?.logoUrl && (
            <div className="mt-3 flex justify-end">
              <Button
                type="button"
                variant="primary"
                size="sm"
                loading={logoUrlMutation.isPending}
                onClick={() => logoUrlMutation.mutate(logoUrlDraft)}
              >
                Save logo URL
              </Button>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
