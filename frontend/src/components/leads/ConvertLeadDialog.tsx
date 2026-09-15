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
import { convertLead, type Lead } from '@/lib/api/leads';
import { leadKeys } from '@/lib/queryKeys';

export interface ConvertLeadDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  lead: Lead;
}

// POST /leads/{id}/convert — idempotent on the backend (re-calling on an
// already-converted lead just returns the existing result), so no
// "already converted" guard is needed here beyond the natural flow of
// the detail page only offering this action while status !== 'won'.
export function ConvertLeadDialog({ open, onOpenChange, lead }: ConvertLeadDialogProps) {
  const queryClient = useQueryClient();
  const [createProject, setCreateProject] = useState(false);
  const [projectName, setProjectName] = useState('');

  const mutation = useMutation({
    mutationFn: () =>
      convertLead(lead.id, {
        createProject,
        projectName: createProject && projectName.trim() ? projectName.trim() : undefined,
      }),
    onSuccess: (updated) => {
      queryClient.invalidateQueries({ queryKey: leadKeys.detail(updated.id) });
      queryClient.invalidateQueries({ queryKey: leadKeys.lists() });
      toast.success(
        updated.convertedProjectId ? 'Lead converted — client and project created' : 'Lead converted to client',
      );
      handleOpenChange(false);
    },
    onError: (error: unknown) => {
      toast.error(error instanceof ApiError ? error.message : 'Something went wrong converting this lead.');
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
          <DialogTitle>Convert lead to client</DialogTitle>
          <DialogDescription>
            "{lead.name}" will become a real client in your workspace, using this lead's own contact details.
          </DialogDescription>
        </DialogHeader>

        <div className="flex flex-col gap-4">
          <div className="flex items-center justify-between gap-4">
            <div className="flex flex-col">
              <Label htmlFor="convert-create-project">Also create a project</Label>
              <span className="text-caption text-text-tertiary">Starts a new project for the converted client.</span>
            </div>
            <Switch id="convert-create-project" checked={createProject} onCheckedChange={setCreateProject} />
          </div>

          {createProject && (
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="convert-project-name">Project name (optional)</Label>
              <Input
                id="convert-project-name"
                placeholder={lead.name}
                value={projectName}
                onChange={(e) => setProjectName(e.target.value)}
              />
            </div>
          )}
        </div>

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
            Convert lead
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
