import { Info } from 'lucide-react';
import { PageHeader } from '@/components/common/PageHeader';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Avatar, AvatarFallback, initialsOf } from '@/components/ui/avatar';
import { Badge } from '@/components/ui/badge';
import { useAuth } from '@/context/AuthContext';
import { formatDate } from '@/lib/format';

function Field({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex flex-col gap-0.5">
      <span className="text-caption text-text-tertiary">{label}</span>
      <span className="text-body text-text-primary">{value}</span>
    </div>
  );
}

// Read-only (Phase 21): GET /auth/me is the only identity endpoint that
// exists — there is no PATCH /auth/me or any other profile-edit endpoint
// anywhere in the backend today, confirmed by a full read of
// apps/authentication/urls.py and views.py. Editable name/email fields
// would be UI that lies about what the product can actually do, so this
// page shows the real data without a form.
export default function ProfilePage() {
  const { user } = useAuth();

  return (
    <div className="flex flex-col gap-6">
      <PageHeader title="Profile" description="Your account details." />

      <Alert variant="info">
        <AlertDescription>
          Editing your profile isn't available yet — the backend has no endpoint to update your name or email. This
          page shows your account as it exists today.
        </AlertDescription>
      </Alert>

      <Card>
        <CardHeader>
          <CardTitle>Account</CardTitle>
          <CardDescription>Managed by your company administrator.</CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col gap-5">
          <div className="flex items-center gap-3">
            <Avatar className="size-14">
              <AvatarFallback seed={user?.id ?? ''}>{user ? initialsOf(user.name) : ''}</AvatarFallback>
            </Avatar>
            <div className="flex flex-col">
              <span className="text-h4 text-text-primary">{user?.name}</span>
              <span className="text-small text-text-secondary">{user?.email}</span>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <Field label="Status" value={<Badge variant={user?.status === 'active' ? 'success' : 'neutral'}>{user?.status}</Badge>} />
            <Field label="Account type" value={user?.isStaff ? 'Platform staff' : 'Company user'} />
            <Field label="Member since" value={user ? formatDate(user.createdAt) : '—'} />
            <Field label="Last updated" value={user ? formatDate(user.updatedAt) : '—'} />
          </div>

          <p className="flex items-center gap-1.5 text-caption text-text-tertiary">
            <Info className="size-3.5" />
            To change your name or email, contact your company administrator.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
