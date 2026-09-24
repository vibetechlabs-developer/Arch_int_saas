import { useState } from 'react';
import { zodResolver } from '@hookform/resolvers/zod';
import { useForm } from 'react-hook-form';
import { z } from 'zod';
import { useMutation } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { motion, useReducedMotion } from 'framer-motion';
import { Building2, MailCheck } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Alert } from '@/components/ui/alert';
import { ApiError } from '@/lib/api/client';
import { requestPasswordReset } from '@/lib/api/auth';

const schema = z.object({
  email: z.string().min(1, 'Email is required').email('Enter a valid email address'),
});
type FormValues = z.infer<typeof schema>;

// The backend's POST /auth/forgot-password deliberately answers the same
// way whether or not the email has an account (anti-enumeration), so this
// page's confirmation copy has to be just as noncommittal -- "if an account
// exists", never "we sent it to you".
export default function ForgotPasswordPage() {
  const shouldReduceMotion = useReducedMotion();
  const [sentTo, setSentTo] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<FormValues>({ resolver: zodResolver(schema) });

  const mutation = useMutation({
    mutationFn: (values: FormValues) => requestPasswordReset(values.email),
    onSuccess: (_data, values) => setSentTo(values.email),
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

        {sentTo ? (
          <div className="flex flex-col items-center gap-4 text-center">
            <MailCheck className="size-8 text-success-text" />
            <div className="flex flex-col gap-1">
              <h1 className="text-h1 font-medium tracking-tight text-text-primary">Check your email</h1>
              <p className="text-body text-text-secondary">
                If an account exists for <strong className="font-medium text-text-primary">{sentTo}</strong>, we've sent a
                link to reset your password. It expires in 1 hour.
              </p>
            </div>
            <p className="text-small text-text-tertiary">
              Nothing after a few minutes? Check your spam folder, or make sure you used the email your admin signed
              you up with.
            </p>
          </div>
        ) : (
          <>
            <div className="flex flex-col gap-1 text-center">
              <h1 className="text-h1 font-medium tracking-tight text-text-primary">Forgot your password?</h1>
              <p className="text-body text-text-secondary">
                Enter your email and we'll send you a link to set a new one.
              </p>
            </div>

            <form onSubmit={handleSubmit((values) => mutation.mutate(values))} className="flex flex-col gap-5" noValidate>
              <div className="flex flex-col gap-1.5">
                <Label htmlFor="forgot-email">Email</Label>
                <Input
                  id="forgot-email"
                  type="email"
                  autoComplete="email"
                  autoFocus
                  invalid={!!errors.email}
                  aria-describedby={errors.email ? 'forgot-email-error' : undefined}
                  {...register('email')}
                />
                {errors.email && (
                  <p id="forgot-email-error" className="text-small text-danger-text">
                    {errors.email.message}
                  </p>
                )}
              </div>

              {mutation.isError && (
                <Alert variant="destructive">
                  {mutation.error instanceof ApiError
                    ? mutation.error.message
                    : 'Something went wrong. Please try again.'}
                </Alert>
              )}

              <Button type="submit" variant="primary" size="lg" loading={mutation.isPending} className="mt-1 w-full">
                Send reset link
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
