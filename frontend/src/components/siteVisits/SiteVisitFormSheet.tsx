import { useEffect, useState } from 'react';
import { zodResolver } from '@hookform/resolvers/zod';
import { useForm } from 'react-hook-form';
import { z } from 'zod';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Alert } from '@/components/ui/alert';
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetDescription } from '@/components/ui/sheet';
import { CompanyMemberCombobox } from '@/components/projects/CompanyMemberCombobox';
import { ProjectCombobox } from '@/components/projects/ProjectCombobox';
import { LeadCombobox } from '@/components/leads/LeadCombobox';
import { ApiError } from '@/lib/api/client';
import { createSiteVisit, updateSiteVisit, type SiteVisit, type SiteVisitInput } from '@/lib/api/siteVisits';
import { siteVisitKeys } from '@/lib/queryKeys';

const siteVisitSchema = z.object({
  visitDate: z.string().min(1, 'A visit date/time is required'),
  address: z.string().max(500).optional(),
  measurements: z.string().optional(),
  requirements: z.string().optional(),
  notes: z.string().optional(),
  budget: z.string().optional(),
  siteConditions: z.string().optional(),
  followUpActions: z.string().optional(),
});

type SiteVisitFormValues = z.infer<typeof siteVisitSchema>;

const EMPTY_VALUES: SiteVisitFormValues = {
  visitDate: '',
  address: '',
  measurements: '',
  requirements: '',
  notes: '',
  budget: '',
  siteConditions: '',
  followUpActions: '',
};

function toDatetimeLocal(iso: string | null): string {
  if (!iso) return '';
  const date = new Date(iso);
  const pad = (n: number) => String(n).padStart(2, '0');
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

export interface SiteVisitFormSheetProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  siteVisit?: SiteVisit;
  onSaved?: (siteVisit: SiteVisit) => void;
}

// Same Sheet drives both create and edit, mirroring LeadFormSheet's
// structure. Lead/project links are only settable at create time (no
// "reassign a site visit" flow is documented) — edit mode shows them
// as static text instead of pretending they can be changed, matching
// ProjectFormSheet's identical treatment of its own immutable client field.
export function SiteVisitFormSheet({ open, onOpenChange, siteVisit, onSaved }: SiteVisitFormSheetProps) {
  const isEdit = !!siteVisit;
  const queryClient = useQueryClient();
  const [leadId, setLeadId] = useState<string | null>(null);
  const [projectId, setProjectId] = useState<string | null>(null);
  const [linkError, setLinkError] = useState<string | null>(null);
  const [assignedToId, setAssignedToId] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    reset,
    setError,
    formState: { errors, isSubmitting },
  } = useForm<SiteVisitFormValues>({ resolver: zodResolver(siteVisitSchema), defaultValues: EMPTY_VALUES });

  useEffect(() => {
    if (!open) return;
    setLinkError(null);
    if (siteVisit) {
      reset({
        visitDate: toDatetimeLocal(siteVisit.visitDate),
        address: siteVisit.address,
        measurements: siteVisit.measurements,
        requirements: siteVisit.requirements,
        notes: siteVisit.notes,
        budget: siteVisit.budget ?? '',
        siteConditions: siteVisit.siteConditions,
        followUpActions: siteVisit.followUpActions,
      });
      setLeadId(siteVisit.leadId);
      setProjectId(siteVisit.projectId);
      setAssignedToId(siteVisit.assignedToId);
    } else {
      reset(EMPTY_VALUES);
      setLeadId(null);
      setProjectId(null);
      setAssignedToId(null);
    }
  }, [open, siteVisit, reset]);

  const mutation = useMutation({
    mutationFn: (values: SiteVisitFormValues) => {
      const input: SiteVisitInput = {
        visitDate: values.visitDate ? new Date(values.visitDate).toISOString() : '',
        assignedToId: assignedToId || null,
        address: values.address || '',
        measurements: values.measurements || '',
        requirements: values.requirements || '',
        notes: values.notes || '',
        budget: values.budget || null,
        siteConditions: values.siteConditions || '',
        followUpActions: values.followUpActions || '',
      };
      if (isEdit) return updateSiteVisit(siteVisit!.id, input);
      return createSiteVisit({ ...input, leadId, projectId });
    },
    onSuccess: (saved) => {
      queryClient.invalidateQueries({ queryKey: siteVisitKeys.lists() });
      if (isEdit) queryClient.invalidateQueries({ queryKey: siteVisitKeys.detail(saved.id) });
      toast.success(isEdit ? 'Site visit updated' : 'Site visit scheduled');
      onOpenChange(false);
      onSaved?.(saved);
    },
    onError: (error: unknown) => {
      if (error instanceof ApiError && error.code === 'VALIDATION_ERROR') {
        for (const detail of error.details) {
          if (detail.field === 'leadId' || detail.field === 'projectId') {
            setLinkError(detail.issue);
            continue;
          }
          if (detail.field in EMPTY_VALUES) {
            setError(detail.field as keyof SiteVisitFormValues, { message: detail.issue });
          }
        }
        return;
      }
      toast.error(error instanceof ApiError ? error.message : 'Something went wrong. Please try again.');
    },
  });

  const onSubmit = (values: SiteVisitFormValues) => {
    if (!isEdit && !leadId && !projectId) {
      setLinkError('Link this visit to a lead or a project.');
      return;
    }
    mutation.mutate(values);
  };

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent className="overflow-y-auto">
        <SheetHeader>
          <SheetTitle>{isEdit ? 'Edit site visit' : 'Schedule a site visit'}</SheetTitle>
          <SheetDescription>
            {isEdit ? 'Update the details captured for this visit.' : 'Schedule a visit against a lead or a project.'}
          </SheetDescription>
        </SheetHeader>

        <form onSubmit={handleSubmit(onSubmit)} className="flex flex-1 flex-col gap-5" noValidate>
          {!isEdit && (
            <div className="grid grid-cols-2 gap-4">
              <div className="flex flex-col gap-1.5">
                <Label>Lead</Label>
                <LeadCombobox value={leadId} onSelect={(id) => { setLeadId(id); setLinkError(null); }} invalid={!!linkError} />
              </div>
              <div className="flex flex-col gap-1.5">
                <Label>Project</Label>
                <ProjectCombobox
                  value={projectId}
                  onSelect={(id) => { setProjectId(id); setLinkError(null); }}
                  invalid={!!linkError}
                />
              </div>
            </div>
          )}
          {isEdit && (
            <div className="flex flex-col gap-1.5">
              <Label>Linked to</Label>
              <p className="rounded-md border border-border-subtle bg-surface-secondary px-3 py-2 text-body text-text-secondary">
                {[siteVisit!.leadName, siteVisit!.projectName].filter(Boolean).join(' · ') || 'Not linked'}
              </p>
            </div>
          )}
          {linkError && <p className="text-small text-danger-text">{linkError}</p>}

          <div className="flex flex-col gap-1.5">
            <Label htmlFor="site-visit-date">Visit date</Label>
            <Input id="site-visit-date" type="datetime-local" invalid={!!errors.visitDate} {...register('visitDate')} />
            {errors.visitDate && <p className="text-small text-danger-text">{errors.visitDate.message}</p>}
          </div>

          <div className="flex flex-col gap-1.5">
            <Label htmlFor="site-visit-address">Address</Label>
            <Input id="site-visit-address" invalid={!!errors.address} {...register('address')} />
            {errors.address && <p className="text-small text-danger-text">{errors.address.message}</p>}
          </div>

          <div className="flex flex-col gap-1.5">
            <div className="flex items-center justify-between">
              <Label>Assigned to</Label>
              {assignedToId && (
                <button
                  type="button"
                  onClick={() => setAssignedToId(null)}
                  className="text-caption text-text-tertiary hover:text-text-primary"
                >
                  Clear
                </button>
              )}
            </div>
            <CompanyMemberCombobox value={assignedToId} onSelect={setAssignedToId} />
          </div>

          <div className="flex flex-col gap-1.5">
            <Label htmlFor="site-visit-budget">Budget</Label>
            <Input id="site-visit-budget" type="number" step="0.01" invalid={!!errors.budget} {...register('budget')} />
            {errors.budget && <p className="text-small text-danger-text">{errors.budget.message}</p>}
          </div>

          <div className="flex flex-col gap-1.5">
            <Label htmlFor="site-visit-measurements">Measurements</Label>
            <Textarea id="site-visit-measurements" rows={3} {...register('measurements')} />
          </div>

          <div className="flex flex-col gap-1.5">
            <Label htmlFor="site-visit-requirements">Requirements</Label>
            <Textarea id="site-visit-requirements" rows={3} {...register('requirements')} />
          </div>

          <div className="flex flex-col gap-1.5">
            <Label htmlFor="site-visit-conditions">Site conditions</Label>
            <Textarea id="site-visit-conditions" rows={3} {...register('siteConditions')} />
          </div>

          <div className="flex flex-col gap-1.5">
            <Label htmlFor="site-visit-follow-up">Follow-up actions</Label>
            <Textarea id="site-visit-follow-up" rows={3} {...register('followUpActions')} />
          </div>

          <div className="flex flex-col gap-1.5">
            <Label htmlFor="site-visit-notes">Notes</Label>
            <Textarea id="site-visit-notes" rows={3} {...register('notes')} />
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
              {isEdit ? 'Save changes' : 'Schedule visit'}
            </Button>
          </div>
        </form>
      </SheetContent>
    </Sheet>
  );
}
