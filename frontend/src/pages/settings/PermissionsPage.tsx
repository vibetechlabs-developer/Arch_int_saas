import { useQuery } from '@tanstack/react-query';
import { KeyRound } from 'lucide-react';
import { PageHeader } from '@/components/common/PageHeader';
import { ErrorState } from '@/components/common/ErrorState';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { getPermissions, groupPermissionsByModule } from '@/lib/api/permissions';
import { permissionKeys } from '@/lib/queryKeys';

// Read-only reference (Phase 20) — kept as its own page rather than nested
// in Role edit, since it's genuinely useful independent of any one role
// (e.g. deciding what a NEW role should grant before creating it).
export default function PermissionsPage() {
  const { data: permissions, isLoading, isError, error, refetch } = useQuery({
    queryKey: permissionKeys.all,
    queryFn: getPermissions,
  });

  if (isError) {
    return <ErrorState error={error} onRetry={() => refetch()} />;
  }

  const groups = permissions ? groupPermissionsByModule(permissions) : [];

  return (
    <div className="flex flex-col gap-6">
      <PageHeader title="Permission catalog" description="Every permission code available to assign to a role." />

      {isLoading ? (
        <div className="flex flex-col gap-3">
          <Skeleton className="h-40 w-full" />
          <Skeleton className="h-40 w-full" />
        </div>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2">
          {groups.map((group) => (
            <Card key={group.module}>
              <CardHeader>
                <CardTitle className="capitalize">
                  <KeyRound className="size-4 text-text-tertiary" />
                  {group.module}
                </CardTitle>
              </CardHeader>
              <CardContent className="flex flex-col gap-3">
                {group.permissions.map((permission) => (
                  <div key={permission.code} className="flex flex-col gap-0.5">
                    <div className="flex items-center gap-2">
                      <Badge variant="neutral">{permission.action}</Badge>
                      <code className="text-caption text-text-tertiary">{permission.code}</code>
                    </div>
                    <p className="text-small text-text-secondary">{permission.description}</p>
                  </div>
                ))}
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
