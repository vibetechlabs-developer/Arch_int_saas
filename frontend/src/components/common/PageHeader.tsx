import type { ReactNode } from 'react';

export interface PageHeaderProps {
  title: string;
  description?: string;
  actions?: ReactNode;
  eyebrow?: string;
}

// Shared page-level header: title + optional description on the left,
// primary/secondary actions on the right. Used by every list/detail page
// so heading scale and spacing stay identical across modules.
export function PageHeader({ title, description, actions, eyebrow }: PageHeaderProps) {
  return (
    <div className="flex flex-wrap items-start justify-between gap-4">
      <div className="flex flex-col gap-1">
        {eyebrow && <span className="text-label text-text-tertiary">{eyebrow}</span>}
        <h2 className="text-h1 font-medium tracking-tight text-text-primary">{title}</h2>
        {description && <p className="text-body text-text-secondary">{description}</p>}
      </div>
      {actions && <div className="flex items-center gap-2">{actions}</div>}
    </div>
  );
}
