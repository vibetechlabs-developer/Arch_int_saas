import { Component, type ErrorInfo, type ReactNode } from 'react';
import { TriangleAlert } from 'lucide-react';
import { Button } from '@/components/ui/button';

interface Props {
  children: ReactNode;
  // When this changes (e.g. the route), a previously-caught error is
  // cleared -- navigating away from a crashed page shouldn't leave the
  // whole app stuck on the error screen.
  resetKey?: string;
  // Full-viewport treatment for the outermost boundary; the in-shell one
  // stays inside the content area so the sidebar keeps working.
  fullScreen?: boolean;
}

interface State {
  hasError: boolean;
}

// Without this, any render-time exception unmounts the whole React tree and
// leaves a blank white page with no explanation and no way out.
export class ErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false };

  static getDerivedStateFromError(): State {
    return { hasError: true };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error('Unhandled UI error', error, info.componentStack);
  }

  componentDidUpdate(prev: Props) {
    if (this.state.hasError && prev.resetKey !== this.props.resetKey) {
      this.setState({ hasError: false });
    }
  }

  render() {
    if (!this.state.hasError) return this.props.children;

    return (
      <div
        className={
          this.props.fullScreen
            ? 'flex min-h-screen flex-col items-center justify-center gap-4 bg-app px-6 text-center'
            : 'flex flex-col items-center gap-4 py-20 text-center'
        }
        role="alert"
      >
        <TriangleAlert className="size-8 text-warning-text" />
        <div className="flex flex-col gap-1">
          <h1 className="text-h2 text-text-primary">Something went wrong</h1>
          <p className="max-w-sm text-body text-text-secondary">
            This page hit an unexpected problem. Your data is safe — try reloading, and let your admin know if it keeps
            happening.
          </p>
        </div>
        <Button variant="primary" onClick={() => window.location.reload()}>
          Reload page
        </Button>
      </div>
    );
  }
}
