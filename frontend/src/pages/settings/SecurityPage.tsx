import { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { toast } from 'sonner';
import { KeyRound, ShieldQuestion } from 'lucide-react';
import { PageHeader } from '@/components/common/PageHeader';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { ApiError } from '@/lib/api/client';
import { requestPasswordReset } from '@/lib/api/auth';
import { useAuth } from '@/context/AuthContext';

// Only ships the one capability the backend actually supports (Phase 22):
// sending a password-reset email via the existing forgot-password flow,
// pre-targeted at the caller's own address. There is no in-session
// change-password endpoint, no session list, and no MFA anywhere in this
// backend — none of those are faked here.
export default function SecurityPage() {
  const { user } = useAuth();
  const [sent, setSent] = useState(false);

  const mutation = useMutation({
    mutationFn: () => requestPasswordReset(user!.email),
    onSuccess: () => {
      setSent(true);
      toast.success('Password reset email sent');
    },
    onError: (error: unknown) => {
      toast.error(error instanceof ApiError ? error.message : 'Failed to send reset email.');
    },
  });

  return (
    <div className="flex flex-col gap-6">
      <PageHeader title="Security" description="Password and login security." />

      <Card>
        <CardHeader>
          <CardTitle>
            <KeyRound className="size-4 text-text-tertiary" />
            Password
          </CardTitle>
          <CardDescription>
            Send a password reset link to {user?.email}. It expires after a short window, matching the same flow
            used from the login screen.
          </CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col gap-3">
          {sent && (
            <Alert variant="success">
              <AlertDescription>
                If this email is registered and active, reset instructions have been sent. Check your inbox.
              </AlertDescription>
            </Alert>
          )}
          <Button
            variant="outline"
            className="w-fit"
            loading={mutation.isPending}
            onClick={() => mutation.mutate()}
          >
            Send password reset email
          </Button>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>
            <ShieldQuestion className="size-4 text-text-tertiary" />
            Two-factor authentication
          </CardTitle>
          <CardDescription>Not available yet.</CardDescription>
        </CardHeader>
        <CardContent>
          <p className="text-small text-text-secondary">
            This account is not currently protected by two-factor authentication or session management — those
            capabilities don't exist in the platform yet.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
