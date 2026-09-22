import { useState } from 'react';
import { Link, Navigate, useNavigate, useParams } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { ArrowLeft, Banknote, Building2, FileWarning, KeyRound, Pencil, ReceiptText, Trash2 } from 'lucide-react';
import { PageHeader } from '@/components/common/PageHeader';
import { ErrorState } from '@/components/common/ErrorState';
import { ConfirmationDialog } from '@/components/common/ConfirmationDialog';
import { StatusBadge } from '@/components/common/StatusBadge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { Button } from '@/components/ui/button';
import { ApiError } from '@/lib/api/client';
import { deleteCompany, getCompany } from '@/lib/api/company';
import { platformCompanyKeys } from '@/lib/queryKeys';
import { formatDateTime } from '@/lib/format';
import { CompanyFormSheet } from '@/components/platform/CompanyFormSheet';
import { SetOwnerPasswordDialog } from '@/components/platform/SetOwnerPasswordDialog';

export default function PlatformCompanyDetailPage() {
  const { companyId } = useParams<{ companyId: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [editOpen, setEditOpen] = useState(false);
  const [deleteOpen, setDeleteOpen] = useState(false);
  const [ownerPasswordOpen, setOwnerPasswordOpen] = useState(false);

  const { data: company, isLoading, isError, error, refetch } = useQuery({
    queryKey: platformCompanyKeys.detail(companyId!),
    queryFn: () => getCompany(companyId!),
    enabled: !!companyId,
  });

  const deleteMutation = useMutation({
    mutationFn: () => deleteCompany(companyId!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: platformCompanyKeys.lists() });
      toast.success('Company deleted');
      navigate('/platform/companies', { replace: true });
    },
    onError: (mutationError: unknown) => {
      toast.error(mutationError instanceof ApiError ? mutationError.message : 'Failed to delete company.');
      setDeleteOpen(false);
    },
  });

  if (!companyId) return <Navigate to="/platform/companies" replace />;

  if (isError) {
    const notFound = error instanceof ApiError && error.code === 'NOT_FOUND';
    if (notFound) {
      return (
        <div className="flex flex-col items-center gap-3 py-16 text-center">
          <FileWarning className="size-6 text-text-tertiary" />
          <div className="flex flex-col gap-1">
            <p className="text-body font-medium text-text-primary">Company not found</p>
            <p className="text-small text-text-secondary">It may have been deleted.</p>
          </div>
          <Button variant="secondary" size="sm" asChild className="mt-1">
            <Link to="/platform/companies">Back to Companies</Link>
          </Button>
        </div>
      );
    }
    return <ErrorState error={error} onRetry={() => refetch()} />;
  }

  return (
    <div className="flex flex-col gap-6">
      <Button variant="ghost" size="sm" className="w-fit gap-1.5 text-text-secondary" asChild>
        <Link to="/platform/companies">
          <ArrowLeft className="size-4" />
          Back to Companies
        </Link>
      </Button>

      {isLoading || !company ? (
        <DetailSkeleton />
      ) : (
        <>
          <PageHeader
            title={company.name}
            description={`Currency ${company.currency}`}
            actions={
              <>
                <StatusBadge status={company.status} />
                <Button variant="outline" onClick={() => setOwnerPasswordOpen(true)}>
                  <KeyRound />
                  Set Owner Password
                </Button>
                <Button variant="outline" onClick={() => setEditOpen(true)}>
                  <Pencil />
                  Edit
                </Button>
                <Button variant="destructive" onClick={() => setDeleteOpen(true)}>
                  <Trash2 />
                  Delete
                </Button>
              </>
            }
          />

          <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
            <Card className="lg:col-span-2">
              <CardHeader>
                <CardTitle>
                  <Building2 className="size-4 text-accent-500" />
                  Tenant details
                </CardTitle>
              </CardHeader>
              <CardContent className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                <InfoRow icon={Banknote} label="Currency" value={company.currency} />
                <InfoRow icon={ReceiptText} label="GSTIN" value={company.gstNumber ?? ''} mono />
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Metadata</CardTitle>
              </CardHeader>
              <CardContent className="flex flex-col gap-3">
                <div className="flex flex-col gap-0.5">
                  <span className="text-caption text-text-tertiary">Created</span>
                  <span className="text-small text-text-primary">{formatDateTime(company.createdAt)}</span>
                </div>
                <div className="flex flex-col gap-0.5">
                  <span className="text-caption text-text-tertiary">Last updated</span>
                  <span className="text-small text-text-primary">{formatDateTime(company.updatedAt)}</span>
                </div>
              </CardContent>
            </Card>
          </div>

          <CompanyFormSheet open={editOpen} onOpenChange={setEditOpen} company={company} />

          <SetOwnerPasswordDialog
            open={ownerPasswordOpen}
            onOpenChange={setOwnerPasswordOpen}
            companyId={company.id}
            companyName={company.name}
          />

          <ConfirmationDialog
            open={deleteOpen}
            onOpenChange={setDeleteOpen}
            title="Delete this company?"
            description={`This soft-deletes "${company.name}" and everything scoped to it.`}
            confirmLabel="Delete company"
            destructive
            loading={deleteMutation.isPending}
            onConfirm={() => deleteMutation.mutate()}
          />
        </>
      )}
    </div>
  );
}

function InfoRow({ icon: Icon, label, value, mono }: { icon: typeof Banknote; label: string; value: string; mono?: boolean }) {
  return (
    <div className="flex items-start gap-2.5">
      <Icon className="mt-0.5 size-4 shrink-0 text-text-tertiary" />
      <div className="flex flex-col gap-0.5">
        <span className="text-caption text-text-tertiary">{label}</span>
        <span className={mono ? 'text-small tabular-nums text-text-primary' : 'text-small text-text-primary'}>
          {value || '—'}
        </span>
      </div>
    </div>
  );
}

function DetailSkeleton() {
  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-col gap-2">
        <Skeleton className="h-3 w-24" />
        <Skeleton className="h-8 w-64" />
        <Skeleton className="h-4 w-48" />
      </div>
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <Card className="flex flex-col gap-4 p-5 lg:col-span-2">
          <Skeleton className="h-4 w-40" />
          <Skeleton className="h-4 w-full" />
          <Skeleton className="h-4 w-2/3" />
        </Card>
        <Card className="flex flex-col gap-4 p-5">
          <Skeleton className="h-4 w-24" />
          <Skeleton className="h-4 w-32" />
        </Card>
      </div>
    </div>
  );
}
