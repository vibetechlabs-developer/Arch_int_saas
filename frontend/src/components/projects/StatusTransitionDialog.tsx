import { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import { Alert } from '@/components/ui/alert';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { StatusBadge, humanizeStatus } from '@/components/common/StatusBadge';
import { ApiError } from '@/lib/api/client';
import { PROJECT_STATUSES, transitionProjectStatus, type Project, type ProjectStatus } from '@/lib/api/projects';
import { projectKeys } from '@/lib/queryKeys';

export interface StatusTransitionDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  project: Project;
}

// The backend doesn't expose which transitions are currently reachable
// (apps/projects/models.py::get_allowed_next_statuses is server-side-only
// business logic) — so this offers every other status and lets
// PATCH /projects/{id}/status be the sole authority. An attempt the graph
// rejects comes back as 409 CONFLICT and is shown inline, not duplicated
// or pre-validated on the frontend.
export function StatusTransitionDialog({ open, onOpenChange, project }: StatusTransitionDialogProps) {
  const queryClient = useQueryClient();
  const [target, setTarget] = useState<ProjectStatus | ''>('');

  const mutation = useMutation({
    mutationFn: (status: ProjectStatus) => transitionProjectStatus(project.id, status),
    onSuccess: (updated) => {
      queryClient.invalidateQueries({ queryKey: projectKeys.detail(updated.id) });
      queryClient.invalidateQueries({ queryKey: projectKeys.lists() });
      toast.success(`Project moved to ${humanizeStatus(updated.status)}`);
      onOpenChange(false);
      setTarget('');
    },
    onError: () => {
      // Conflict (409) and any other failure are both rendered inline below
      // via mutation.error — kept in the dialog so the user can pick again.
    },
  });

  const handleOpenChange = (next: boolean) => {
    if (!next) {
      setTarget('');
      mutation.reset();
    }
    onOpenChange(next);
  };

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="max-w-sm">
        <DialogHeader>
          <DialogTitle>Change project status</DialogTitle>
          <DialogDescription>
            Currently <StatusBadge status={project.status} />. Choose the new status — the backend will confirm
            whether this move is allowed.
          </DialogDescription>
        </DialogHeader>

        <Select value={target} onValueChange={(value) => setTarget(value as ProjectStatus)}>
          <SelectTrigger>
            <SelectValue placeholder="Select a status" />
          </SelectTrigger>
          <SelectContent>
            {PROJECT_STATUSES.filter((status) => status !== project.status).map((status) => (
              <SelectItem key={status} value={status}>
                {humanizeStatus(status)}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        {mutation.isError && (
          <Alert variant="destructive">
            {mutation.error instanceof ApiError
              ? mutation.error.message
              : 'Something went wrong changing the status.'}
          </Alert>
        )}

        <DialogFooter>
          <Button variant="outline" onClick={() => handleOpenChange(false)} disabled={mutation.isPending}>
            Cancel
          </Button>
          <Button
            variant="primary"
            disabled={!target}
            loading={mutation.isPending}
            onClick={() => target && mutation.mutate(target)}
          >
            Confirm change
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
