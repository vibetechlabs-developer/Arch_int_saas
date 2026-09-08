import { useState } from 'react';
import { Link, NavLink, Navigate, Outlet, useNavigate, useParams } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { motion, useReducedMotion } from 'framer-motion';
import { ArrowLeft, FileWarning, MoreHorizontal, Pencil, Repeat, Trash2 } from 'lucide-react';
import { ErrorState } from '@/components/common/ErrorState';
import { StatusBadge } from '@/components/common/StatusBadge';
import { ConfirmationDialog } from '@/components/common/ConfirmationDialog';
import { Card } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { ApiError } from '@/lib/api/client';
import { deleteProject, getProject } from '@/lib/api/projects';
import { projectKeys } from '@/lib/queryKeys';
import { formatDate } from '@/lib/format';
import { pageTransition, pageTransitionReduced } from '@/lib/motion';
import { cn } from '@/lib/utils';
import { ProjectFormSheet } from '@/components/projects/ProjectFormSheet';
import { StatusTransitionDialog } from '@/components/projects/StatusTransitionDialog';

const WORKSPACE_TABS = [
  { label: 'Overview', path: 'overview' },
  { label: 'Team', path: 'team' },
];

export default function ProjectWorkspaceLayout() {
  const { projectId } = useParams<{ projectId: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const shouldReduceMotion = useReducedMotion();
  const [editOpen, setEditOpen] = useState(false);
  const [statusOpen, setStatusOpen] = useState(false);
  const [deleteOpen, setDeleteOpen] = useState(false);

  const { data: project, isLoading, isError, error, refetch } = useQuery({
    queryKey: projectKeys.detail(projectId!),
    queryFn: () => getProject(projectId!),
    enabled: !!projectId,
  });

  const deleteMutation = useMutation({
    mutationFn: () => deleteProject(projectId!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: projectKeys.lists() });
      toast.success('Project deleted');
      navigate('/projects', { replace: true });
    },
    onError: (mutationError: unknown) => {
      toast.error(mutationError instanceof ApiError ? mutationError.message : 'Failed to delete project.');
      setDeleteOpen(false);
    },
  });

  if (!projectId) return <Navigate to="/projects" replace />;

  if (isError) {
    const notFound = error instanceof ApiError && error.code === 'NOT_FOUND';
    if (notFound) {
      return (
        <div className="flex flex-col items-center gap-3 py-16 text-center">
          <FileWarning className="size-6 text-text-tertiary" />
          <div className="flex flex-col gap-1">
            <p className="text-body font-medium text-text-primary">Project not found</p>
            <p className="text-small text-text-secondary">
              It may have been deleted, or you don't have access to it.
            </p>
          </div>
          <Button variant="secondary" size="sm" asChild className="mt-1">
            <Link to="/projects">Back to Projects</Link>
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
        <Link to="/projects">
          <ArrowLeft className="size-4" />
          Back to Projects
        </Link>
      </Button>

      {isLoading || !project ? (
        <WorkspaceSkeleton />
      ) : (
        <>
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div className="flex flex-col gap-1.5">
              <span className="text-label text-text-tertiary">{project.clientName}</span>
              <h2 className="text-h1 font-medium tracking-tight text-text-primary">{project.name}</h2>
              <div className="flex flex-wrap items-center gap-2">
                <StatusBadge status={project.status} />
                {project.priority && <Badge variant="neutral">{project.priority}</Badge>}
                <span className="text-small text-text-tertiary">
                  {project.startDate ? formatDate(project.startDate) : 'No start date'}
                  {' — '}
                  {project.deadline ? formatDate(project.deadline) : 'No deadline'}
                </span>
              </div>
            </div>

            <div className="flex items-center gap-2">
              <Button variant="outline" onClick={() => setEditOpen(true)}>
                <Pencil />
                Edit
              </Button>
              <Button variant="outline" onClick={() => setStatusOpen(true)}>
                <Repeat />
                Change status
              </Button>
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button variant="ghost" size="icon" aria-label="More project actions">
                    <MoreHorizontal />
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end">
                  <DropdownMenuItem destructive onSelect={() => setDeleteOpen(true)}>
                    <Trash2 className="size-4" />
                    Delete project
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            </div>
          </div>

          <nav className="flex gap-1 border-b border-border-subtle">
            {WORKSPACE_TABS.map((tab) => (
              <NavLink
                key={tab.path}
                to={tab.path}
                className={({ isActive }) =>
                  cn(
                    'border-b-2 px-3 py-2 text-body transition-colors duration-fast',
                    isActive
                      ? 'border-accent-500 text-text-primary'
                      : 'border-transparent text-text-secondary hover:text-text-primary',
                  )
                }
              >
                {tab.label}
              </NavLink>
            ))}
          </nav>

          <Outlet context={{ project }} />

          <ProjectFormSheet open={editOpen} onOpenChange={setEditOpen} project={project} />
          <StatusTransitionDialog open={statusOpen} onOpenChange={setStatusOpen} project={project} />

          <ConfirmationDialog
            open={deleteOpen}
            onOpenChange={setDeleteOpen}
            title="Delete this project?"
            description={`This removes "${project.name}" and its team assignments. Related BOQs, quotations, invoices, and expenses are not affected.`}
            confirmLabel="Delete project"
            destructive
            loading={deleteMutation.isPending}
            onConfirm={() => deleteMutation.mutate()}
          />
        </>
      )}
    </motion.div>
  );
}

function WorkspaceSkeleton() {
  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-col gap-2">
        <Skeleton className="h-3 w-32" />
        <Skeleton className="h-8 w-72" />
        <Skeleton className="h-5 w-56" />
      </div>
      <Card className="flex flex-col gap-4 p-5">
        <Skeleton className="h-4 w-40" />
        <Skeleton className="h-4 w-full" />
        <Skeleton className="h-4 w-2/3" />
      </Card>
    </div>
  );
}
