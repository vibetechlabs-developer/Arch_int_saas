import { useState } from 'react';
import { Link, Navigate, useNavigate, useParams } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { motion, useReducedMotion } from 'framer-motion';
import {
  ArrowLeft,
  ArrowRightLeft,
  Building2,
  FileWarning,
  Mail,
  Pencil,
  Phone,
  Tag,
  ThumbsDown,
  Trash2,
  User,
  UserCheck,
} from 'lucide-react';
import { PageHeader } from '@/components/common/PageHeader';
import { ErrorState } from '@/components/common/ErrorState';
import { ConfirmationDialog } from '@/components/common/ConfirmationDialog';
import { StatusBadge } from '@/components/common/StatusBadge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { Button } from '@/components/ui/button';
import { ApiError } from '@/lib/api/client';
import { deleteLead, getLead } from '@/lib/api/leads';
import { leadKeys } from '@/lib/queryKeys';
import { formatDateTime } from '@/lib/format';
import { pageTransition, pageTransitionReduced } from '@/lib/motion';
import { LeadFormSheet } from '@/components/leads/LeadFormSheet';
import { LeadStatusDialog } from '@/components/leads/LeadStatusDialog';
import { MarkLostDialog } from '@/components/leads/MarkLostDialog';
import { ConvertLeadDialog } from '@/components/leads/ConvertLeadDialog';

export default function LeadDetailPage() {
  const { leadId } = useParams<{ leadId: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const shouldReduceMotion = useReducedMotion();
  const [editOpen, setEditOpen] = useState(false);
  const [deleteOpen, setDeleteOpen] = useState(false);
  const [statusOpen, setStatusOpen] = useState(false);
  const [markLostOpen, setMarkLostOpen] = useState(false);
  const [convertOpen, setConvertOpen] = useState(false);

  const { data: lead, isLoading, isError, error, refetch } = useQuery({
    queryKey: leadKeys.detail(leadId!),
    queryFn: () => getLead(leadId!),
    enabled: !!leadId,
  });

  const deleteMutation = useMutation({
    mutationFn: () => deleteLead(leadId!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: leadKeys.lists() });
      toast.success('Lead deleted');
      navigate('/leads', { replace: true });
    },
    onError: (mutationError: unknown) => {
      toast.error(mutationError instanceof ApiError ? mutationError.message : 'Failed to delete lead.');
      setDeleteOpen(false);
    },
  });

  if (!leadId) return <Navigate to="/leads" replace />;

  if (isError) {
    const notFound = error instanceof ApiError && error.code === 'NOT_FOUND';
    if (notFound) {
      return (
        <div className="flex flex-col items-center gap-3 py-16 text-center">
          <FileWarning className="size-6 text-text-tertiary" />
          <div className="flex flex-col gap-1">
            <p className="text-body font-medium text-text-primary">Lead not found</p>
            <p className="text-small text-text-secondary">
              It may have been deleted, or you don't have access to it.
            </p>
          </div>
          <Button variant="secondary" size="sm" asChild className="mt-1">
            <Link to="/leads">Back to Leads</Link>
          </Button>
        </div>
      );
    }
    return <ErrorState error={error} onRetry={() => refetch()} />;
  }

  const isTerminal = lead?.status === 'won' || lead?.status === 'lost';

  return (
    <motion.div
      variants={shouldReduceMotion ? pageTransitionReduced : pageTransition}
      initial="hidden"
      animate="show"
      className="flex flex-col gap-6"
    >
      <Button variant="ghost" size="sm" className="w-fit gap-1.5 text-text-secondary" asChild>
        <Link to="/leads">
          <ArrowLeft className="size-4" />
          Back to Leads
        </Link>
      </Button>

      {isLoading || !lead ? (
        <DetailSkeleton />
      ) : (
        <>
          <PageHeader
            eyebrow={lead.companyName || undefined}
            title={lead.name}
            description={[lead.email, lead.mobile].filter(Boolean).join(' · ') || 'No contact details on file.'}
            actions={
              <>
                <StatusBadge status={lead.status} />
                {!isTerminal && (
                  <>
                    <Button variant="outline" onClick={() => setStatusOpen(true)}>
                      <ArrowRightLeft />
                      Change Status
                    </Button>
                    <Button variant="outline" onClick={() => setConvertOpen(true)}>
                      <UserCheck />
                      Convert
                    </Button>
                    <Button variant="outline" onClick={() => setMarkLostOpen(true)}>
                      <ThumbsDown />
                      Mark Lost
                    </Button>
                  </>
                )}
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
                <InfoRow icon={Mail} label="Email" value={lead.email} />
                <InfoRow icon={Phone} label="Mobile" value={lead.mobile} />
                <InfoRow icon={Building2} label="Company" value={lead.companyName} />
                <InfoRow icon={Tag} label="Source" value={lead.source} />
                <InfoRow icon={User} label="Assigned to" value={lead.assignedToName ?? ''} />
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Metadata</CardTitle>
              </CardHeader>
              <CardContent className="flex flex-col gap-3">
                <div className="flex flex-col gap-0.5">
                  <span className="text-caption text-text-tertiary">Added</span>
                  <span className="text-small text-text-primary">{formatDateTime(lead.createdAt)}</span>
                </div>
                <div className="flex flex-col gap-0.5">
                  <span className="text-caption text-text-tertiary">Last updated</span>
                  <span className="text-small text-text-primary">{formatDateTime(lead.updatedAt)}</span>
                </div>
                {lead.followUpReminderAt && (
                  <div className="flex flex-col gap-0.5">
                    <span className="text-caption text-text-tertiary">Follow-up reminder</span>
                    <span className="text-small text-text-primary">{formatDateTime(lead.followUpReminderAt)}</span>
                  </div>
                )}
              </CardContent>
            </Card>

            {lead.status === 'lost' && lead.lossReason && (
              <Card className="lg:col-span-3">
                <CardHeader>
                  <CardTitle>Loss reason</CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="whitespace-pre-wrap text-body text-text-secondary">{lead.lossReason}</p>
                </CardContent>
              </Card>
            )}

            {lead.status === 'won' && (lead.convertedClientId || lead.convertedProjectId) && (
              <Card className="lg:col-span-3">
                <CardHeader>
                  <CardTitle>
                    <UserCheck className="size-4 text-success-text" />
                    Converted
                  </CardTitle>
                </CardHeader>
                <CardContent className="flex flex-col gap-2">
                  {lead.convertedClientId && (
                    <Link to={`/clients/${lead.convertedClientId}`} className="text-small text-accent-500 hover:underline">
                      View client: {lead.convertedClientName}
                    </Link>
                  )}
                  {lead.convertedProjectId && (
                    <Link
                      to={`/projects/${lead.convertedProjectId}`}
                      className="text-small text-accent-500 hover:underline"
                    >
                      View project: {lead.convertedProjectName}
                    </Link>
                  )}
                </CardContent>
              </Card>
            )}

            {lead.notes && (
              <Card className="lg:col-span-3">
                <CardHeader>
                  <CardTitle>Notes</CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="whitespace-pre-wrap text-body text-text-secondary">{lead.notes}</p>
                </CardContent>
              </Card>
            )}
          </div>

          <LeadFormSheet open={editOpen} onOpenChange={setEditOpen} lead={lead} />
          <LeadStatusDialog open={statusOpen} onOpenChange={setStatusOpen} lead={lead} />
          <MarkLostDialog open={markLostOpen} onOpenChange={setMarkLostOpen} lead={lead} />
          <ConvertLeadDialog open={convertOpen} onOpenChange={setConvertOpen} lead={lead} />

          <ConfirmationDialog
            open={deleteOpen}
            onOpenChange={setDeleteOpen}
            title="Delete this lead?"
            description={`This removes "${lead.name}" from your pipeline.`}
            confirmLabel="Delete lead"
            destructive
            loading={deleteMutation.isPending}
            onConfirm={() => deleteMutation.mutate()}
          />
        </>
      )}
    </motion.div>
  );
}

function InfoRow({ icon: Icon, label, value }: { icon: typeof Mail; label: string; value: string }) {
  return (
    <div className="flex items-start gap-2.5">
      <Icon className="mt-0.5 size-4 shrink-0 text-text-tertiary" />
      <div className="flex flex-col gap-0.5">
        <span className="text-caption text-text-tertiary">{label}</span>
        <span className="text-small text-text-primary">{value || '—'}</span>
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
