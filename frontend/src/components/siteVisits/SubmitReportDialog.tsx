import { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import { Alert } from '@/components/ui/alert';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { ApiError } from '@/lib/api/client';
import { submitSiteVisitReport, type SiteVisit } from '@/lib/api/siteVisits';
import { siteVisitKeys } from '@/lib/queryKeys';

export interface SubmitReportDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  siteVisit: SiteVisit;
}

// POST /site-visits/{id}/report — idempotent on the backend, and
// "create a project" only succeeds when this visit already has a
// resolved client (from an already-converted lead, or an existing
// project link) — a 409 otherwise, surfaced inline like every other
// dialog in this module (mirrors ConvertLeadDialog's structure).
export function SubmitReportDialog({ open, onOpenChange, siteVisit }: SubmitReportDialogProps) {
  const queryClient = useQueryClient();
  const [createProject, setCreateProject] = useState(false);
  const [projectName, setProjectName] = useState('');

  const canCreateProject = !siteVisit.projectId && !!siteVisit.clientId;

  const mutation = useMutation({
    mutationFn: () =>
      submitSiteVisitReport(siteVisit.id, {
        createProject,
        projectName: createProject && projectName.trim() ? projectName.trim() : undefined,
      }),
    onSuccess: (updated) => {
      queryClient.invalidateQueries({ queryKey: siteVisitKeys.detail(updated.id) });
      queryClient.invalidateQueries({ queryKey: siteVisitKeys.lists() });
      toast.success(updated.projectId ? 'Report submitted — project created' : 'Report submitted');
      handleOpenChange(false);
    },
    onError: (error: unknown) => {
      toast.error(error instanceof ApiError ? error.message : 'Something went wrong submitting this report.');
    },
  });

  const handleOpenChange = (next: boolean) => {
    if (!next) {
      setCreateProject(false);
      setProjectName('');
      mutation.reset();
    }
    onOpenChange(next);
  };

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="max-w-sm">
        <DialogHeader>
          <DialogTitle>Submit site visit report</DialogTitle>
          <DialogDescription>Marks this visit complete, using the details already captured.</DialogDescription>
        </DialogHeader>

        {!siteVisit.projectId && (
          <div className="flex flex-col gap-4">
            <div className="flex items-center justify-between gap-4">
              <div className="flex flex-col">
                <Label htmlFor="report-create-project">Also create a project</Label>
                <span className="text-caption text-text-tertiary">
                  {canCreateProject
                    ? 'Starts a new project for the linked client.'
                    : 'Convert the lead to a client first — no client is linked yet.'}
                </span>
              </div>
              <Switch
                id="report-create-project"
                checked={createProject}
                onCheckedChange={setCreateProject}
                disabled={!canCreateProject}
              />
            </div>

            {createProject && canCreateProject && (
              <div className="flex flex-col gap-1.5">
                <Label htmlFor="report-project-name">Project name (optional)</Label>
                <Input
                  id="report-project-name"
                  placeholder={`${siteVisit.clientName ?? 'Site Visit'} Project`}
                  value={projectName}
                  onChange={(e) => setProjectName(e.target.value)}
                />
              </div>
            )}
          </div>
        )}

        {mutation.isError && (
          <Alert variant="destructive">
            {mutation.error instanceof ApiError ? mutation.error.message : 'Something went wrong.'}
          </Alert>
        )}

        <DialogFooter>
          <Button variant="outline" onClick={() => handleOpenChange(false)} disabled={mutation.isPending}>
            Cancel
          </Button>
          <Button variant="primary" loading={mutation.isPending} onClick={() => mutation.mutate()}>
            Submit report
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
