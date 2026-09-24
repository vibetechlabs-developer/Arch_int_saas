import { Link, useNavigate } from 'react-router-dom';
import { Compass } from 'lucide-react';
import { Button } from '@/components/ui/button';

// Shown for any URL that matches no route. Used to silently redirect to
// the dashboard, which left someone who mistyped a URL or followed a stale
// bookmark wondering why the page they asked for never appeared.
export function NotFoundState({ homeHref = '/dashboard', homeLabel = 'Go to dashboard' }: { homeHref?: string; homeLabel?: string }) {
  const navigate = useNavigate();

  return (
    <div className="flex flex-col items-center gap-4 py-20 text-center">
      <Compass className="size-8 text-text-tertiary" />
      <div className="flex flex-col gap-1">
        <h1 className="text-h2 text-text-primary">We couldn't find that page</h1>
        <p className="max-w-sm text-body text-text-secondary">
          The link may be mistyped, or the page may have been moved or deleted.
        </p>
      </div>
      <div className="flex items-center gap-2">
        <Button variant="outline" onClick={() => navigate(-1)}>
          Go back
        </Button>
        <Button variant="primary" asChild>
          <Link to={homeHref}>{homeLabel}</Link>
        </Button>
      </div>
    </div>
  );
}
