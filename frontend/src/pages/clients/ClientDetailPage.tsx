import { useState } from 'react';
import { Link, Navigate, useNavigate, useParams } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { motion, useReducedMotion } from 'framer-motion';
import { ArrowLeft, Building2, FileWarning, Mail, Pencil, Phone, ReceiptText, Trash2 } from 'lucide-react';
import { PageHeader } from '@/components/common/PageHeader';
import { ErrorState } from '@/components/common/ErrorState';
import { ConfirmationDialog } from '@/components/common/ConfirmationDialog';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { Button } from '@/components/ui/button';
import { ApiError } from '@/lib/api/client';
import { deleteClient, getClient } from '@/lib/api/clients';
import { clientKeys } from '@/lib/queryKeys';
import { formatDateTime } from '@/lib/format';
import { pageTransition, pageTransitionReduced } from '@/lib/motion';
import { ClientFormSheet } from '@/components/clients/ClientFormSheet';

export default function ClientDetailPage() {
  const { clientId } = useParams<{ clientId: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const shouldReduceMotion = useReducedMotion();
  const [editOpen, setEditOpen] = useState(false);
  const [deleteOpen, setDeleteOpen] = useState(false);

  const { data: client, isLoading, isError, error, refetch } = useQuery({
    queryKey: clientKeys.detail(clientId!),
    queryFn: () => getClient(clientId!),
    enabled: !!clientId,
  });

  const deleteMutation = useMutation({
    mutationFn: () => deleteClient(clientId!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: clientKeys.lists() });
      toast.success('Client deleted');
      navigate('/clients', { replace: true });
    },
    onError: (mutationError: unknown) => {
      toast.error(mutationError instanceof ApiError ? mutationError.message : 'Failed to delete client.');
      setDeleteOpen(false);
    },
  });

  if (!clientId) return <Navigate to="/clients" replace />;

  if (isError) {
    const notFound = error instanceof ApiError && error.code === 'NOT_FOUND';
    if (notFound) {
      return (
        <div className="flex flex-col items-center gap-3 py-16 text-center">
          <FileWarning className="size-6 text-text-tertiary" />
          <div className="flex flex-col gap-1">
            <p className="text-body font-medium text-text-primary">Client not found</p>
            <p className="text-small text-text-secondary">
              It may have been deleted, or you don't have access to it.
            </p>
          </div>
          <Button variant="secondary" size="sm" asChild className="mt-1">
            <Link to="/clients">Back to Clients</Link>
          </Button>
        </div>
      );
    }
    return <ErrorState error={error} onRetry={() => refetch()} />;
  }

  return (
    <motion.div
      variants={shouldReduceMotion ? pageTransitionReduced : pageTransition}
      initial="hidden"
      animate="show"
      className="flex flex-col gap-6"
    >
      <Button variant="ghost" size="sm" className="w-fit gap-1.5 text-text-secondary" asChild>
        <Link to="/clients">
          <ArrowLeft className="size-4" />
          Back to Clients
        </Link>
      </Button>

      {isLoading || !client ? (
        <DetailSkeleton />
      ) : (
        <>
          <PageHeader
            eyebrow={client.companyName || undefined}
            title={client.name}
            description={[client.email, client.mobile].filter(Boolean).join(' · ') || 'No contact details on file.'}
            actions={
              <>
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
                  Contact Information
                </CardTitle>
              </CardHeader>
              <CardContent className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                <InfoRow icon={Mail} label="Email" value={client.email} />
                <InfoRow icon={Phone} label="Mobile" value={client.mobile} />
                <InfoRow icon={ReceiptText} label="GSTIN" value={client.gstin} mono />
                <InfoRow icon={Building2} label="Company" value={client.companyName} />
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Metadata</CardTitle>
              </CardHeader>
              <CardContent className="flex flex-col gap-3">
                <div className="flex flex-col gap-0.5">
                  <span className="text-caption text-text-tertiary">Added</span>
                  <span className="text-small text-text-primary">{formatDateTime(client.createdAt)}</span>
                </div>
                <div className="flex flex-col gap-0.5">
                  <span className="text-caption text-text-tertiary">Last updated</span>
                  <span className="text-small text-text-primary">{formatDateTime(client.updatedAt)}</span>
                </div>
              </CardContent>
            </Card>

            {client.notes && (
              <Card className="lg:col-span-3">
                <CardHeader>
                  <CardTitle>Notes</CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="whitespace-pre-wrap text-body text-text-secondary">{client.notes}</p>
                </CardContent>
              </Card>
            )}

            {client.addresses.length > 0 && (
              <Card className="lg:col-span-3">
                <CardHeader>
                  <CardTitle>Addresses</CardTitle>
                </CardHeader>
                <CardContent className="flex flex-col gap-3">
                  {client.addresses.map((address, index) => (
                    <pre
                      key={index}
                      className="overflow-x-auto rounded-md bg-surface-secondary p-3 text-small text-text-secondary"
                    >
                      {JSON.stringify(address, null, 2)}
                    </pre>
                  ))}
                </CardContent>
              </Card>
            )}
          </div>

          <ClientFormSheet open={editOpen} onOpenChange={setEditOpen} client={client} />

          <ConfirmationDialog
            open={deleteOpen}
            onOpenChange={setDeleteOpen}
            title="Delete this client?"
            description={`This removes "${client.name}" from your client list. Projects already linked to them are not affected.`}
            confirmLabel="Delete client"
            destructive
            loading={deleteMutation.isPending}
            onConfirm={() => deleteMutation.mutate()}
          />
        </>
      )}
    </motion.div>
  );
}

function InfoRow({ icon: Icon, label, value, mono }: { icon: typeof Mail; label: string; value: string; mono?: boolean }) {
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
