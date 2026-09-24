import { useState } from 'react';
import { zodResolver } from '@hookform/resolvers/zod';
import { useForm } from 'react-hook-form';
import { z } from 'zod';
import { useMutation } from '@tanstack/react-query';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { motion, useReducedMotion } from 'framer-motion';
import { Building2, CheckCircle2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { PasswordInput } from '@/components/ui/password-input';
import { Label } from '@/components/ui/label';
import { Alert } from '@/components/ui/alert';
import { ApiError } from '@/lib/api/client';
import { resetPassword } from '@/lib/api/auth';

const schema = z
  .object({
    newPassword: z.string().min(8, 'Password must be at least 8 characters'),
    confirmPassword: z.string().min(1, 'Please confirm your password'),
  })
  .refine((data) => data.newPassword === data.confirmPassword, {
    message: "Passwords don't match",
    path: ['confirmPassword'],
  });
type FormValues = z.infer<typeof schema>;

// Genuinely missing route until now (confirmed by a full read of App.tsx
// — no /reset-password page existed despite the backend having supported
// POST /auth/reset-password since Sprint 1). Consumes the same
// single-use token whether it arrived via the existing forgot-password
// email or the new Add User account-setup email — the backend endpoint
// treats both identically, so one page serves both flows.
export default function SetPasswordPage() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const shouldReduceMotion = useReducedMotion();
  const token = searchParams.get('token') ?? '';
  const [success, setSuccess] = useState(false);

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<FormValues>({ resolver: zodResolver(schema) });

  const mutation = useMutation({
    mutationFn: (values: FormValues) => resetPassword(token, values.newPassword),
    onSuccess: () => setSuccess(true),
  });

  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-app px-6 py-12">
      <motion.div
        initial={shouldReduceMotion ? { opacity: 0 } : { opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: shouldReduceMotion ? 0.01 : 0.4, ease: [0.16, 1, 0.3, 1] }}
        className="flex w-full max-w-sm flex-col gap-8"
      >
        <div className="flex flex-col items-center gap-3 text-center">
          <span className="flex size-10 items-center justify-center rounded-lg bg-accent-500 text-text-on-accent">
            <Building2 className="size-5" />
          </span>
          <span className="text-h4 text-text-primary">INT Projects</span>
        </div>

        {success ? (
          <div className="flex flex-col items-center gap-4 text-center">
            <CheckCircle2 className="size-8 text-success-text" />
            <div className="flex flex-col gap-1">
              <h1 className="text-h1 font-medium tracking-tight text-text-primary">Password set</h1>
              <p className="text-body text-text-secondary">You can now sign in with your new password.</p>
            </div>
            <Button variant="primary" size="lg" className="w-full" onClick={() => navigate('/login', { replace: true })}>
              Go to sign in
            </Button>
          </div>
        ) : !token ? (
          <Alert variant="destructive">This link is missing its token. Please use the link from your email.</Alert>
        ) : (
          <>
            <div className="flex flex-col gap-1 text-center">
              <h1 className="text-h1 font-medium tracking-tight text-text-primary">Set your password</h1>
              <p className="text-body text-text-secondary">Choose a password to finish setting up your account.</p>
            </div>

            <form onSubmit={handleSubmit((values) => mutation.mutate(values))} className="flex flex-col gap-5" noValidate>
              <div className="flex flex-col gap-1.5">
                <Label htmlFor="new-password">New password</Label>
                <PasswordInput id="new-password" autoComplete="new-password" autoFocus invalid={!!errors.newPassword} {...register('newPassword')} />
                {errors.newPassword && <p className="text-small text-danger-text">{errors.newPassword.message}</p>}
              </div>

              <div className="flex flex-col gap-1.5">
                <Label htmlFor="confirm-password">Confirm password</Label>
                <PasswordInput id="confirm-password" autoComplete="new-password" invalid={!!errors.confirmPassword} {...register('confirmPassword')} />
                {errors.confirmPassword && <p className="text-small text-danger-text">{errors.confirmPassword.message}</p>}
              </div>

              {mutation.isError && (
                <Alert variant="destructive">
                  {mutation.error instanceof ApiError ? mutation.error.message : 'Something went wrong. Please try again.'}
                </Alert>
              )}

              <Button type="submit" variant="primary" size="lg" loading={mutation.isPending} className="mt-1 w-full">
                Set password
              </Button>
            </form>
          </>
        )}

        <p className="text-center text-small text-text-tertiary">
          <Link to="/login" className="text-accent-500 hover:underline">
            Back to sign in
          </Link>
        </p>
      </motion.div>
    </div>
  );
}
