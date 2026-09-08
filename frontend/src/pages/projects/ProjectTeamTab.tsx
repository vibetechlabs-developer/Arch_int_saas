import { useState } from 'react';
import { useOutletContext } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { Plus, Trash2, UserPlus, Users } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Alert } from '@/components/ui/alert';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Avatar, AvatarFallback, initialsOf } from '@/components/ui/avatar';
import { EmptyState } from '@/components/common/EmptyState';
import { ErrorState } from '@/components/common/ErrorState';
import { ConfirmationDialog } from '@/components/common/ConfirmationDialog';
import { Skeleton } from '@/components/ui/skeleton';
import { CompanyMemberCombobox } from '@/components/projects/CompanyMemberCombobox';
import { ApiError } from '@/lib/api/client';
import {
  addProjectTeamMember,
  getProjectTeam,
  removeProjectTeamMember,
  type Project,
  type ProjectMember,
} from '@/lib/api/projects';
import { projectKeys } from '@/lib/queryKeys';
import { formatDate } from '@/lib/format';

export default function ProjectTeamTab() {
  const { project } = useOutletContext<{ project: Project }>();
  const queryClient = useQueryClient();
  const [addOpen, setAddOpen] = useState(false);
  const [selectedUserId, setSelectedUserId] = useState<string | null>(null);
  const [removingMember, setRemovingMember] = useState<ProjectMember | null>(null);

  const { data: team, isLoading, isError, error, refetch } = useQuery({
    queryKey: projectKeys.team(project.id),
    queryFn: () => getProjectTeam(project.id),
  });

  const addMutation = useMutation({
    mutationFn: (userId: string) => addProjectTeamMember(project.id, userId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: projectKeys.team(project.id) });
      toast.success('Team member added');
      setAddOpen(false);
      setSelectedUserId(null);
    },
    onError: (mutationError: unknown) => {
      // No inline field to attach this to on the combobox — the backend's
      // own validator names this "assignedTo" even for the /team payload's
      // "userId" field, so it's surfaced as-is rather than mismapped.
      if (!(mutationError instanceof ApiError)) {
        toast.error('Failed to add team member.');
        return;
      }
      toast.error(mutationError.details[0]?.issue ?? mutationError.message);
    },
  });

  const removeMutation = useMutation({
    mutationFn: (userId: string) => removeProjectTeamMember(project.id, userId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: projectKeys.team(project.id) });
      toast.success('Team member removed');
      setRemovingMember(null);
    },
    onError: (mutationError: unknown) => {
      toast.error(mutationError instanceof ApiError ? mutationError.message : 'Failed to remove team member.');
      setRemovingMember(null);
    },
  });

  if (isError) {
    return <ErrorState error={error} onRetry={() => refetch()} />;
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <h3 className="text-h3 text-text-primary">Team</h3>
        <Button variant="primary" size="sm" onClick={() => setAddOpen(true)}>
          <Plus />
          Add member
        </Button>
      </div>

      {isLoading ? (
        <div className="flex flex-col gap-2">
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="flex items-center gap-3 rounded-lg border border-border-subtle bg-surface p-4">
              <Skeleton className="size-8 rounded-full" />
              <div className="flex flex-1 flex-col gap-1.5">
                <Skeleton className="h-4 w-40" />
                <Skeleton className="h-3 w-56" />
              </div>
            </div>
          ))}
        </div>
      ) : !team || team.length === 0 ? (
        <div className="rounded-lg border border-border-subtle bg-surface p-4">
          <EmptyState
            icon={Users}
            title="No team members yet"
            description="Add company members to this project's team."
            action={{ label: 'Add member', onClick: () => setAddOpen(true) }}
          />
        </div>
      ) : (
        <div className="flex flex-col divide-y divide-border-subtle rounded-lg border border-border-subtle bg-surface">
          {team.map((member) => (
            <div key={member.id} className="flex items-center justify-between gap-3 p-4">
              <div className="flex items-center gap-3">
                <Avatar>
                  <AvatarFallback seed={member.userId ?? member.id}>
                    {member.userName ? initialsOf(member.userName) : '?'}
                  </AvatarFallback>
                </Avatar>
                <div className="flex flex-col">
                  <span className="text-body font-medium text-text-primary">{member.userName ?? 'Unknown user'}</span>
                  <span className="text-caption text-text-tertiary">{member.userEmail}</span>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <span className="hidden text-caption text-text-tertiary sm:block">
                  Added {formatDate(member.createdAt)}
                  {member.assignedByName ? ` by ${member.assignedByName}` : ''}
                </span>
                <Button
                  variant="ghost"
                  size="icon"
                  aria-label={`Remove ${member.userName ?? 'member'}`}
                  onClick={() => setRemovingMember(member)}
                >
                  <Trash2 className="size-4 text-danger-text" />
                </Button>
              </div>
            </div>
          ))}
        </div>
      )}

      <Dialog open={addOpen} onOpenChange={(open) => { setAddOpen(open); if (!open) setSelectedUserId(null); }}>
        <DialogContent className="max-w-sm">
          <DialogHeader>
            <DialogTitle>
              <UserPlus className="size-4 text-accent-500" />
              Add team member
            </DialogTitle>
            <DialogDescription>Search your company's active members to add them to this project.</DialogDescription>
          </DialogHeader>

          <CompanyMemberCombobox value={selectedUserId} onSelect={setSelectedUserId} />

          {addMutation.isError && (
            <Alert variant="destructive">
              {addMutation.error instanceof ApiError ? addMutation.error.message : 'Something went wrong.'}
            </Alert>
          )}

          <DialogFooter>
            <Button variant="outline" onClick={() => setAddOpen(false)} disabled={addMutation.isPending}>
              Cancel
            </Button>
            <Button
              variant="primary"
              disabled={!selectedUserId}
              loading={addMutation.isPending}
              onClick={() => selectedUserId && addMutation.mutate(selectedUserId)}
            >
              Add to team
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <ConfirmationDialog
        open={!!removingMember}
        onOpenChange={(open) => !open && setRemovingMember(null)}
        title="Remove this team member?"
        description={`${removingMember?.userName ?? 'This person'} will lose access associated with this project's team.`}
        confirmLabel="Remove member"
        destructive
        loading={removeMutation.isPending}
        onConfirm={() => removingMember?.userId && removeMutation.mutate(removingMember.userId)}
      />
    </div>
  );
}
