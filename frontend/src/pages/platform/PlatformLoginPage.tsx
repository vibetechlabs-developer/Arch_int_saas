import { useState } from 'react';
import { zodResolver } from '@hookform/resolvers/zod';
import { useForm } from 'react-hook-form';
import { z } from 'zod';
import { Navigate, useNavigate } from 'react-router-dom';
import { motion, useReducedMotion } from 'framer-motion';
import { ShieldCheck } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { PasswordInput } from '@/components/ui/password-input';
import { Label } from '@/components/ui/label';
import { Alert } from '@/components/ui/alert';
import { useAuth } from '@/context/AuthContext';
import { ApiError } from '@/lib/api/client';

const loginSchema = z.object({
  email: z.string().min(1, 'Email is required').email('Enter a valid email address'),
  password: z.string().min(1, 'Password is required'),
});

type LoginFormValues = z.infer<typeof loginSchema>;

// A deliberately plainer treatment than the tenant LoginPage — this is an
// internal operator console, not a customer-facing surface, so no brand
// panel/marketing copy. Reached only by its own URL; nothing in the
// regular login page links here.
export default function PlatformLoginPage() {
  const { user, isLoading, isPlatformAdmin, loginPlatformAdmin } = useAuth();
  const navigate = useNavigate();
  const [formError, setFormError] = useState<string | null>(null);
  const shouldReduceMotion = useReducedMotion();

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<LoginFormValues>({ resolver: zodResolver(loginSchema) });

  if (!isLoading && user && isPlatformAdmin) {
    return <Navigate to="/platform/companies" replace />;
  }

  const onSubmit = async (values: LoginFormValues) => {
    setFormError(null);
    try {
      await loginPlatformAdmin(values.email, values.password);
      navigate('/platform/companies', { replace: true });
    } catch (error) {
      setFormError(error instanceof ApiError ? error.message : 'Unable to sign in. Please try again.');
    }
  };

  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-app px-6 py-12">
      <div className="flex w-full max-w-sm flex-col gap-8">
        <div className="flex flex-col items-center gap-3 text-center">
          <span className="flex size-10 items-center justify-center rounded-lg bg-surface-secondary text-text-secondary">
            <ShieldCheck className="size-5" />
          </span>
          <span className="text-h4 text-text-primary">INT Projects — Platform Admin</span>
        </div>

        <motion.div
          initial={shouldReduceMotion ? { opacity: 0 } : { opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: shouldReduceMotion ? 0.01 : 0.4, ease: [0.16, 1, 0.3, 1] }}
          className="flex flex-col gap-8"
        >
          <div className="flex flex-col gap-1 text-center">
            <h1 className="font-display text-h2 font-medium tracking-tight text-text-primary">Platform console</h1>
            <p className="text-body text-text-secondary">Restricted to platform super admins.</p>
          </div>

          <form onSubmit={handleSubmit(onSubmit)} className="flex flex-col gap-5" noValidate>
            <div className="flex flex-col gap-1.5">
              <Label htmlFor="platform-email">Email</Label>
              <Input
                id="platform-email"
                type="email"
                autoComplete="email"
                autoFocus
                invalid={!!errors.email}
                aria-describedby={errors.email ? 'platform-email-error' : undefined}
                {...register('email')}
              />
              {errors.email && (
                <p id="platform-email-error" className="text-small text-danger-text">
                  {errors.email.message}
                </p>
              )}
            </div>

            <div className="flex flex-col gap-1.5">
              <Label htmlFor="platform-password">Password</Label>
              <PasswordInput
                id="platform-password"
                autoComplete="current-password"
                invalid={!!errors.password}
                aria-describedby={errors.password ? 'platform-password-error' : undefined}
                {...register('password')}
              />
              {errors.password && (
                <p id="platform-password-error" className="text-small text-danger-text">
                  {errors.password.message}
                </p>
              )}
            </div>

            {formError && <Alert variant="destructive">{formError}</Alert>}

            <Button type="submit" variant="primary" size="lg" loading={isSubmitting} className="mt-1 w-full">
              Sign in
            </Button>
          </form>
        </motion.div>
      </div>
    </div>
  );
}
