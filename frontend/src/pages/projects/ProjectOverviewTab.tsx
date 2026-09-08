import { useOutletContext } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { Building2, Calendar, Clock, Flag, User, Users } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Avatar, AvatarFallback, AvatarGroup, initialsOf } from '@/components/ui/avatar';
import { getProjectTeam, type Project } from '@/lib/api/projects';
import { projectKeys } from '@/lib/queryKeys';
import { formatDate, formatDateTime } from '@/lib/format';

// No `description` field exists on the backend Project model — every value
// shown here comes directly from the real ProjectSerializer payload, no
// invented KPIs or frontend-computed financials.
export default function ProjectOverviewTab() {
  const { project } = useOutletContext<{ project: Project }>();

  const { data: team } = useQuery({
    queryKey: projectKeys.team(project.id),
    queryFn: () => getProjectTeam(project.id),
  });

  return (
    <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
      <Card className="lg:col-span-2">
        <CardHeader>
          <CardTitle>Project Details</CardTitle>
        </CardHeader>
        <CardContent className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <InfoRow icon={Building2} label="Client" value={project.clientName} />
          <InfoRow icon={User} label="Assigned to" value={project.assignedToName ?? '—'} />
          <InfoRow icon={Calendar} label="Start date" value={project.startDate ? formatDate(project.startDate) : '—'} />
          <InfoRow icon={Calendar} label="Deadline" value={project.deadline ? formatDate(project.deadline) : '—'} />
          <InfoRow icon={Flag} label="Priority" value={project.priority || '—'} />
          <InfoRow
            icon={Clock}
            label="Follow-up reminder"
            value={project.followUpReminderAt ? formatDateTime(project.followUpReminderAt) : '—'}
          />
        </CardContent>
      </Card>

      <div className="flex flex-col gap-6">
        <Card>
          <CardHeader>
            <CardTitle>Metadata</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-3">
            <div className="flex flex-col gap-0.5">
              <span className="text-caption text-text-tertiary">Created</span>
              <span className="text-small text-text-primary">{formatDateTime(project.createdAt)}</span>
            </div>
            <div className="flex flex-col gap-0.5">
              <span className="text-caption text-text-tertiary">Last updated</span>
              <span className="text-small text-text-primary">{formatDateTime(project.updatedAt)}</span>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>
              <Users className="size-4 text-accent-500" />
              Team
            </CardTitle>
          </CardHeader>
          <CardContent>
            {team && team.length > 0 ? (
              <AvatarGroup>
                {team.map((member) => (
                  <Avatar key={member.id}>
                    <AvatarFallback seed={member.userId ?? member.id}>
                      {member.userName ? initialsOf(member.userName) : '?'}
                    </AvatarFallback>
                  </Avatar>
                ))}
              </AvatarGroup>
            ) : (
              <p className="text-small text-text-secondary">No team members assigned yet.</p>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

function InfoRow({ icon: Icon, label, value }: { icon: typeof Building2; label: string; value: string }) {
  return (
    <div className="flex items-start gap-2.5">
      <Icon className="mt-0.5 size-4 shrink-0 text-text-tertiary" />
      <div className="flex flex-col gap-0.5">
        <span className="text-caption text-text-tertiary">{label}</span>
        <span className="text-small text-text-primary">{value}</span>
      </div>
    </div>
  );
}
