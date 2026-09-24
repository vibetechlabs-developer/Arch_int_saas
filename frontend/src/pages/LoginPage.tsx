import { useState } from 'react';
import { zodResolver } from '@hookform/resolvers/zod';
import { useForm } from 'react-hook-form';
import { z } from 'zod';
import { Link, Navigate, useLocation, useNavigate } from 'react-router-dom';
import { motion, useReducedMotion } from 'framer-motion';
import { Building2 } from 'lucide-react';
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

export default function LoginPage() {
  const { user, isLoading, login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [formError, setFormError] = useState<string | null>(null);
  const shouldReduceMotion = useReducedMotion();

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<LoginFormValues>({ resolver: zodResolver(loginSchema) });

  if (!isLoading && user) {
    const redirectTo = (location.state as { from?: Location })?.from?.pathname ?? '/dashboard';
    return <Navigate to={redirectTo} replace />;
  }

  const onSubmit = async (values: LoginFormValues) => {
    setFormError(null);
    try {
      await login(values.email, values.password);
      navigate('/dashboard', { replace: true });
    } catch (error) {
      setFormError(error instanceof ApiError ? error.message : 'Unable to sign in. Please try again.');
    }
  };

  return (
    <div className="grid min-h-screen lg:grid-cols-2">
      {/* Brand panel — a deliberate solid accent block, not a gradient or
          glass surface (Design_Principles.md §2 rejects both); the
          architectural line motif is this product's own industry
          identity, not a generic AI decoration. */}
      <div className="relative hidden flex-col justify-between overflow-hidden bg-brand-panel p-12 text-white lg:flex">
        <BlueprintMotif />

        <div className="relative flex items-center gap-3">
          <span className="flex size-9 items-center justify-center rounded-lg bg-white/10 text-white">
            <Building2 className="size-5" />
          </span>
          <span className="text-h4 tracking-tight">INT Projects</span>
        </div>

        <div className="relative flex max-w-md flex-col gap-3">
          <p className="font-display text-h2 font-medium leading-snug tracking-tight text-balance">
            One operating system for client, project, and cash.
          </p>
          <p className="text-body text-white/70">
            Client acquisition, BOQ, quotations, invoices, and profitability — connected end to end for architecture,
            interior design, and turnkey project firms.
          </p>
        </div>
      </div>

      {/* Form panel */}
      <div className="flex flex-col items-center justify-center bg-app px-6 py-12 sm:px-12">
        <div className="flex w-full max-w-sm flex-col gap-8">
          <div className="flex flex-col items-center gap-3 text-center lg:hidden">
            <span className="flex size-10 items-center justify-center rounded-lg bg-accent-500 text-text-on-accent">
              <Building2 className="size-5" />
            </span>
            <span className="text-h4 text-text-primary">INT Projects</span>
          </div>

          <motion.div
            initial={shouldReduceMotion ? { opacity: 0 } : { opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: shouldReduceMotion ? 0.01 : 0.4, ease: [0.16, 1, 0.3, 1] }}
            className="flex flex-col gap-8"
          >
            <div className="flex flex-col gap-1">
              <h1 className="font-display text-h1 font-medium tracking-tight text-text-primary">Welcome back</h1>
              <p className="text-body text-text-secondary">Sign in to your workspace to continue.</p>
            </div>

            <form onSubmit={handleSubmit(onSubmit)} className="flex flex-col gap-5" noValidate>
              <div className="flex flex-col gap-1.5">
                <Label htmlFor="email">Email</Label>
                <Input
                  id="email"
                  type="email"
                  autoComplete="email"
                  autoFocus
                  invalid={!!errors.email}
                  aria-describedby={errors.email ? 'email-error' : undefined}
                  {...register('email')}
                />
                {errors.email && (
                  <p id="email-error" className="text-small text-danger-text">
                    {errors.email.message}
                  </p>
                )}
              </div>

              <div className="flex flex-col gap-1.5">
                <div className="flex items-center justify-between">
                  <Label htmlFor="password">Password</Label>
                  <Link to="/forgot-password" className="text-small text-accent-500 hover:underline">
                    Forgot password?
                  </Link>
                </div>
                <PasswordInput
                  id="password"
                  autoComplete="current-password"
                  invalid={!!errors.password}
                  aria-describedby={errors.password ? 'password-error' : undefined}
                  {...register('password')}
                />
                {errors.password && (
                  <p id="password-error" className="text-small text-danger-text">
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
    </div>
  );
}

// A restrained architectural motif for the brand panel — a blueprint grid
// plus a stylized skyline line-drawing, both stroke-only at low opacity so
// the panel reads as a deliberate brand surface, not a stock illustration.
function BlueprintMotif() {
  return (
    <svg
      className="pointer-events-none absolute inset-0 h-full w-full"
      viewBox="0 0 600 800"
      fill="none"
      preserveAspectRatio="xMidYMax slice"
      aria-hidden="true"
    >
      <defs>
        <pattern id="blueprint-grid" width="40" height="40" patternUnits="userSpaceOnUse">
          <path d="M 40 0 L 0 0 0 40" fill="none" stroke="white" strokeOpacity="0.06" strokeWidth="1" />
        </pattern>
      </defs>
      <rect width="600" height="800" fill="url(#blueprint-grid)" />

      {/* Skyline silhouette, anchored to the bottom edge */}
      <g stroke="white" strokeOpacity="0.16" strokeWidth="1.5">
        <rect x="60" y="520" width="90" height="280" />
        <line x1="60" y1="560" x2="150" y2="560" />
        <line x1="60" y1="600" x2="150" y2="600" />
        <line x1="60" y1="640" x2="150" y2="640" />
        <line x1="60" y1="680" x2="150" y2="680" />
        <line x1="60" y1="720" x2="150" y2="720" />
        <line x1="60" y1="760" x2="150" y2="760" />

        <rect x="170" y="440" width="110" height="360" />
        <line x1="170" y1="480" x2="280" y2="480" />
        <line x1="170" y1="520" x2="280" y2="520" />
        <line x1="170" y1="560" x2="280" y2="560" />
        <line x1="170" y1="600" x2="280" y2="600" />
        <line x1="170" y1="640" x2="280" y2="640" />
        <line x1="170" y1="680" x2="280" y2="680" />
        <line x1="170" y1="720" x2="280" y2="720" />
        <line x1="170" y1="760" x2="280" y2="760" />

        <rect x="300" y="360" width="80" height="440" />
        <polyline points="300,360 340,300 380,360" strokeOpacity="0.22" />
        <line x1="300" y1="400" x2="380" y2="400" />
        <line x1="300" y1="440" x2="380" y2="440" />
        <line x1="300" y1="480" x2="380" y2="480" />
        <line x1="300" y1="520" x2="380" y2="520" />
        <line x1="300" y1="560" x2="380" y2="560" />
        <line x1="300" y1="600" x2="380" y2="600" />
        <line x1="300" y1="640" x2="380" y2="640" />
        <line x1="300" y1="680" x2="380" y2="680" />
        <line x1="300" y1="720" x2="380" y2="720" />
        <line x1="300" y1="760" x2="380" y2="760" />

        <rect x="400" y="500" width="100" height="300" />
        <line x1="400" y1="540" x2="500" y2="540" />
        <line x1="400" y1="580" x2="500" y2="580" />
        <line x1="400" y1="620" x2="500" y2="620" />
        <line x1="400" y1="660" x2="500" y2="660" />
        <line x1="400" y1="700" x2="500" y2="700" />
        <line x1="400" y1="740" x2="500" y2="740" />
      </g>
      <line x1="0" y1="800" x2="600" y2="800" stroke="white" strokeOpacity="0.25" strokeWidth="2" />
    </svg>
  );
}
