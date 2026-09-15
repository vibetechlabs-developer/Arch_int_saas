import { useState } from 'react';
import { Link, Navigate, useNavigate, useParams } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { motion, useReducedMotion } from 'framer-motion';
import {
  ArrowLeft,
  Banknote,
  Building2,
  CalendarCheck,
  CircleCheck,
  FileWarning,
  MapPin,
  Pencil,
  Trash2,
  User,
} from 'lucide-react';
import { PageHeader } from '@/components/common/PageHeader';
import { ErrorState } from '@/components/common/ErrorState';
import { ConfirmationDialog } from '@/components/common/ConfirmationDialog';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { Button } from '@/components/ui/button';
import { ApiError } from '@/lib/api/client';
import { deleteSiteVisit, getSiteVisit } from '@/lib/api/siteVisits';
import { siteVisitKeys } from '@/lib/queryKeys';
import { formatDateTime } from '@/lib/format';
import { pageTransition, pageTransitionReduced } from '@/lib/motion';
import { SiteVisitFormSheet } from '@/components/siteVisits/SiteVisitFormSheet';
import { SubmitReportDialog } from '@/components/siteVisits/SubmitReportDialog';

export default function SiteVisitDetailPage() {
  const { siteVisitId } = useParams<{ siteVisitId: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const shouldReduceMotion = useReducedMotion();
  const [editOpen, setEditOpen] = useState(false);
  const [deleteOpen, setDeleteOpen] = useState(false);
  const [reportOpen, setReportOpen] = useState(false);

  const { data: siteVisit, isLoading, isError, error, refetch } = useQuery({
    queryKey: siteVisitKeys.detail(siteVisitId!),
    queryFn: () => getSiteVisit(siteVisitId!),
    enabled: !!siteVisitId,
  });

  const deleteMutation = useMutation({
    mutationFn: () => deleteSiteVisit(siteVisitId!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: siteVisitKeys.lists() });
      toast.success('Site visit deleted');
      navigate('/site-visits', { replace: true });
    },
    onError: (mutationError: unknown) => {
      toast.error(mutationError instanceof ApiError ? mutationError.message : 'Failed to delete site visit.');
      setDeleteOpen(false);
    },
  });

  if (!siteVisitId) return <Navigate to="/site-visits" replace />;

  if (isError) {
    const notFound = error instanceof ApiError && error.code === 'NOT_FOUND';
    if (notFound) {
      return (
        <div className="flex flex-col items-center gap-3 py-16 text-center">
          <FileWarning className="size-6 text-text-tertiary" />
          <div className="flex flex-col gap-1">
            <p className="text-body font-medium text-text-primary">Site visit not found</p>
            <p className="text-small text-text-secondary">
              It may have been deleted, or you don't have access to it.
            </p>
          </div>
          <Button variant="secondary" size="sm" asChild className="mt-1">
            <Link to="/site-visits">Back to Site Visits</Link>
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
        <Link to="/site-visits">
          <ArrowLeft className="size-4" />
          Back to Site Visits
        </Link>
      </Button>

      {isLoading || !siteVisit ? (
        <DetailSkeleton />
      ) : (
        <>
          <PageHeader
            eyebrow={siteVisit.clientName || undefined}
            title={siteVisit.projectName || siteVisit.leadName || 'Site Visit'}
            description={formatDateTime(siteVisit.visitDate)}
            actions={
              <>
                <Badge variant={siteVisit.isCompleted ? 'success' : 'neutral'}>
                  {siteVisit.isCompleted ? 'Completed' : 'Scheduled'}
                </Badge>
                {!siteVisit.isCompleted && (
                  <Button variant="outline" onClick={() => setReportOpen(true)}>
                    <CircleCheck />
                    Submit Report
                  </Button>
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
                  <MapPin className="size-4 text-accent-500" />
                  Visit Details
                </CardTitle>
              </CardHeader>
              <CardContent className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                <InfoRow icon={MapPin} label="Address" value={siteVisit.address} />
                <InfoRow icon={User} label="Assigned to" value={siteVisit.assignedToName ?? ''} />
                <InfoRow icon={Building2} label="Client" value={siteVisit.clientName ?? ''} />
                <InfoRow icon={Banknote} label="Budget" value={siteVisit.budget ? `₹${siteVisit.budget}` : ''} />
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Metadata</CardTitle>
              </CardHeader>
              <CardContent className="flex flex-col gap-3">
                <div className="flex flex-col gap-0.5">
                  <span className="text-caption text-text-tertiary">Created</span>
                  <span className="text-small text-text-primary">{formatDateTime(siteVisit.createdAt)}</span>
                </div>
                {siteVisit.reportSubmittedAt && (
                  <div className="flex flex-col gap-0.5">
                    <span className="text-caption text-text-tertiary">Report submitted</span>
                    <span className="text-small text-text-primary">{formatDateTime(siteVisit.reportSubmittedAt)}</span>
                  </div>
                )}
              </CardContent>
            </Card>

            {(siteVisit.measurements || siteVisit.requirements) && (
              <Card className="lg:col-span-3">
                <CardHeader>
                  <CardTitle>Measurements & Requirements</CardTitle>
                </CardHeader>
                <CardContent className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                  {siteVisit.measurements && (
                    <div className="flex flex-col gap-1">
                      <span className="text-caption text-text-tertiary">Measurements</span>
                      <p className="whitespace-pre-wrap text-body text-text-secondary">{siteVisit.measurements}</p>
                    </div>
                  )}
                  {siteVisit.requirements && (
                    <div className="flex flex-col gap-1">
                      <span className="text-caption text-text-tertiary">Requirements</span>
                      <p className="whitespace-pre-wrap text-body text-text-secondary">{siteVisit.requirements}</p>
                    </div>
                  )}
                </CardContent>
              </Card>
            )}

            {siteVisit.siteConditions && (
              <Card className="lg:col-span-3">
                <CardHeader>
                  <CardTitle>Site conditions</CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="whitespace-pre-wrap text-body text-text-secondary">{siteVisit.siteConditions}</p>
                </CardContent>
              </Card>
            )}

            {siteVisit.followUpActions && (
              <Card className="lg:col-span-3">
                <CardHeader>
                  <CardTitle>Follow-up actions</CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="whitespace-pre-wrap text-body text-text-secondary">{siteVisit.followUpActions}</p>
                </CardContent>
              </Card>
            )}

            {siteVisit.notes && (
              <Card className="lg:col-span-3">
                <CardHeader>
                  <CardTitle>Notes</CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="whitespace-pre-wrap text-body text-text-secondary">{siteVisit.notes}</p>
                </CardContent>
              </Card>
            )}
          </div>

          <SiteVisitFormSheet open={editOpen} onOpenChange={setEditOpen} siteVisit={siteVisit} />
          <SubmitReportDialog open={reportOpen} onOpenChange={setReportOpen} siteVisit={siteVisit} />

          <ConfirmationDialog
            open={deleteOpen}
            onOpenChange={setDeleteOpen}
            title="Delete this site visit?"
            description="This removes the scheduled visit and everything captured for it."
            confirmLabel="Delete visit"
            destructive
            loading={deleteMutation.isPending}
            onConfirm={() => deleteMutation.mutate()}
          />
        </>
      )}
    </motion.div>
  );
}

function InfoRow({ icon: Icon, label, value }: { icon: typeof MapPin; label: string; value: string }) {
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
