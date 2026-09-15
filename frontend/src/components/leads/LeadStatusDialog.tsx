import { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import { Alert } from '@/components/ui/alert';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { StatusBadge, humanizeStatus } from '@/components/common/StatusBadge';
import { ApiError } from '@/lib/api/client';
import { LEAD_STATUS_TRANSITION_OPTIONS, transitionLeadStatus, type Lead, type LeadStatus } from '@/lib/api/leads';
import { leadKeys } from '@/lib/queryKeys';

export interface LeadStatusDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  lead: Lead;
}

// Mirrors apps.projects StatusTransitionDialog's pattern exactly: the
// backend graph (apps/leads/models.py::get_allowed_next_statuses) is the
// sole authority — this only pre-excludes `won`, which is never reachable
// via this endpoint at all (see LEAD_STATUS_TRANSITION_OPTIONS). Any other
// invalid move comes back as 409 and is shown inline.
export function LeadStatusDialog({ open, onOpenChange, lead }: LeadStatusDialogProps) {
  const queryClient = useQueryClient();
  const [target, setTarget] = useState<LeadStatus | ''>('');

  const mutation = useMutation({
    mutationFn: (status: LeadStatus) => transitionLeadStatus(lead.id, status),
    onSuccess: (updated) => {
      queryClient.invalidateQueries({ queryKey: leadKeys.detail(updated.id) });
      queryClient.invalidateQueries({ queryKey: leadKeys.lists() });
      toast.success(`Lead moved to ${humanizeStatus(updated.status)}`);
      onOpenChange(false);
      setTarget('');
    },
    onError: () => {
      // Conflict (409) and any other failure are both rendered inline below.
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
          <DialogTitle>Change lead status</DialogTitle>
          <DialogDescription>
            Currently <StatusBadge status={lead.status} />. Choose the new status — the backend will confirm whether
            this move is allowed.
          </DialogDescription>
        </DialogHeader>

        <Select value={target} onValueChange={(value) => setTarget(value as LeadStatus)}>
          <SelectTrigger>
            <SelectValue placeholder="Select a status" />
          </SelectTrigger>
          <SelectContent>
            {LEAD_STATUS_TRANSITION_OPTIONS.filter((status) => status !== lead.status).map((status) => (
              <SelectItem key={status} value={status}>
                {humanizeStatus(status)}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        {mutation.isError && (
          <Alert variant="destructive">
            {mutation.error instanceof ApiError ? mutation.error.message : 'Something went wrong changing the status.'}
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
