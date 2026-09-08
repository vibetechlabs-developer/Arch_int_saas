import { useEffect, useState } from 'react';
import { zodResolver } from '@hookform/resolvers/zod';
import { useForm } from 'react-hook-form';
import { z } from 'zod';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Alert } from '@/components/ui/alert';
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetDescription } from '@/components/ui/sheet';
import { ClientCombobox } from '@/components/clients/ClientCombobox';
import { CompanyMemberCombobox } from '@/components/projects/CompanyMemberCombobox';
import { ApiError } from '@/lib/api/client';
import { createProject, updateProject, type Project, type ProjectMutableInput } from '@/lib/api/projects';
import { projectKeys } from '@/lib/queryKeys';

const projectSchema = z.object({
  name: z.string().trim().min(1, 'Project name is required').max(255),
  startDate: z.string().optional(),
  deadline: z.string().optional(),
  priority: z.string().max(50).optional(),
  followUpReminderAt: z.string().optional(),
});

type ProjectFormValues = z.infer<typeof projectSchema>;

const EMPTY_VALUES: ProjectFormValues = { name: '', startDate: '', deadline: '', priority: '', followUpReminderAt: '' };

function toDatetimeLocal(iso: string | null): string {
  if (!iso) return '';
  const date = new Date(iso);
  const pad = (n: number) => String(n).padStart(2, '0');
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

export interface ProjectFormSheetProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  project?: Project;
  onSaved?: (project: Project) => void;
}

// Same Sheet drives both create and edit. Client is required to create a
// project but is not editable afterward (no documented "reassign client"
// endpoint) — the combobox only appears in create mode; edit mode shows
// the client as a static field instead of pretending it can be changed.
export function ProjectFormSheet({ open, onOpenChange, project, onSaved }: ProjectFormSheetProps) {
  const isEdit = !!project;
  const queryClient = useQueryClient();
  const [clientId, setClientId] = useState<string | null>(null);
  const [clientError, setClientError] = useState<string | null>(null);
  const [assignedTo, setAssignedTo] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    reset,
    setError,
    formState: { errors, isSubmitting },
  } = useForm<ProjectFormValues>({ resolver: zodResolver(projectSchema), defaultValues: EMPTY_VALUES });

  useEffect(() => {
    if (!open) return;
    setClientError(null);
    if (project) {
      reset({
        name: project.name,
        startDate: project.startDate ?? '',
        deadline: project.deadline ?? '',
        priority: project.priority,
        followUpReminderAt: toDatetimeLocal(project.followUpReminderAt),
      });
      setClientId(project.clientId);
      setAssignedTo(project.assignedToId);
    } else {
      reset(EMPTY_VALUES);
      setClientId(null);
      setAssignedTo(null);
    }
  }, [open, project, reset]);

  const mutation = useMutation({
    mutationFn: (values: ProjectFormValues) => {
      const mutableInput: ProjectMutableInput = {
        name: values.name,
        startDate: values.startDate || null,
        deadline: values.deadline || null,
        priority: values.priority || '',
        assignedTo: assignedTo || null,
        followUpReminderAt: values.followUpReminderAt ? new Date(values.followUpReminderAt).toISOString() : null,
      };
      return isEdit
        ? updateProject(project!.id, mutableInput)
        : createProject({ ...mutableInput, clientId: clientId! });
    },
    onSuccess: (saved) => {
      queryClient.invalidateQueries({ queryKey: projectKeys.lists() });
      if (isEdit) queryClient.invalidateQueries({ queryKey: projectKeys.detail(saved.id) });
      toast.success(isEdit ? 'Project updated' : 'Project created');
      onOpenChange(false);
      onSaved?.(saved);
    },
    onError: (error: unknown) => {
      if (error instanceof ApiError && error.code === 'VALIDATION_ERROR') {
        for (const detail of error.details) {
          if (detail.field === 'clientId' || detail.field === 'assignedTo') {
            setClientError(detail.field === 'clientId' ? detail.issue : null);
            if (detail.field === 'assignedTo') toast.error(detail.issue);
            continue;
          }
          if (detail.field in EMPTY_VALUES) {
            setError(detail.field as keyof ProjectFormValues, { message: detail.issue });
          }
        }
        return;
      }
      toast.error(error instanceof ApiError ? error.message : 'Something went wrong. Please try again.');
    },
  });

  const onSubmit = (values: ProjectFormValues) => {
    if (!isEdit && !clientId) {
      setClientError('Select a client for this project.');
      return;
    }
    mutation.mutate(values);
  };

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent className="overflow-y-auto">
        <SheetHeader>
          <SheetTitle>{isEdit ? 'Edit project' : 'New project'}</SheetTitle>
          <SheetDescription>
            {isEdit ? 'Update this project’s details.' : 'Set up a new project for a client.'}
          </SheetDescription>
        </SheetHeader>

        <form onSubmit={handleSubmit(onSubmit)} className="flex flex-1 flex-col gap-5" noValidate>
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="project-name">Project name</Label>
            <Input id="project-name" invalid={!!errors.name} {...register('name')} />
            {errors.name && <p className="text-small text-danger-text">{errors.name.message}</p>}
          </div>

          <div className="flex flex-col gap-1.5">
            <Label>Client</Label>
            {isEdit ? (
              <p className="rounded-md border border-border-subtle bg-surface-secondary px-3 py-2 text-body text-text-secondary">
                {project!.clientName}
              </p>
            ) : (
              <>
                <ClientCombobox value={clientId} onSelect={(id) => { setClientId(id); setClientError(null); }} invalid={!!clientError} />
                {clientError && <p className="text-small text-danger-text">{clientError}</p>}
              </>
            )}
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="project-start-date">Start date</Label>
              <Input id="project-start-date" type="date" invalid={!!errors.startDate} {...register('startDate')} />
              {errors.startDate && <p className="text-small text-danger-text">{errors.startDate.message}</p>}
            </div>
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="project-deadline">Deadline</Label>
              <Input id="project-deadline" type="date" invalid={!!errors.deadline} {...register('deadline')} />
              {errors.deadline && <p className="text-small text-danger-text">{errors.deadline.message}</p>}
            </div>
          </div>

          <div className="flex flex-col gap-1.5">
            <Label htmlFor="project-priority">Priority</Label>
            <Input id="project-priority" placeholder="e.g. High" invalid={!!errors.priority} {...register('priority')} />
            {errors.priority && <p className="text-small text-danger-text">{errors.priority.message}</p>}
          </div>

          <div className="flex flex-col gap-1.5">
            <div className="flex items-center justify-between">
              <Label>Assigned to</Label>
              {assignedTo && (
                <button
                  type="button"
                  onClick={() => setAssignedTo(null)}
                  className="text-caption text-text-tertiary hover:text-text-primary"
                >
                  Clear
                </button>
              )}
            </div>
            <CompanyMemberCombobox value={assignedTo} onSelect={setAssignedTo} />
          </div>

          <div className="flex flex-col gap-1.5">
            <Label htmlFor="project-follow-up">Follow-up reminder</Label>
            <Input
              id="project-follow-up"
              type="datetime-local"
              invalid={!!errors.followUpReminderAt}
              {...register('followUpReminderAt')}
            />
            {errors.followUpReminderAt && (
              <p className="text-small text-danger-text">{errors.followUpReminderAt.message}</p>
            )}
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
              {isEdit ? 'Save changes' : 'Create project'}
            </Button>
          </div>
        </form>
      </SheetContent>
    </Sheet>
  );
}
