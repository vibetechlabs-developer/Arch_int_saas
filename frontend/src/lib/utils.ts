import { clsx, type ClassValue } from 'clsx';
import { extendTailwindMerge } from 'tailwind-merge';

// tailwind-merge's default config only knows Tailwind's own color/font-size
// scale. It has no way to know that this project's custom `text-*` classes
// split into two unrelated groups -- text COLOR (text-ink-text, text-text-
// primary, ...) and text SIZE (text-body, text-h1, ...) -- both defined in
// tailwind.config.ts's `theme.extend`. Without telling it so, it treats
// every `text-*` class as one ambiguous group and silently drops all but
// the last one whenever both a color and a size class land on the same
// element (e.g. Button's `variant` class `text-ink-text` collides with its
// `size` class `text-body`, so the color never reaches the DOM -- the text
// then falls back to `--text-primary`, which is unreadable against an
// `--ink-bg` fill in both themes). Registering the two scales as their own
// groups is the documented fix for a custom theme like this one.
const twMerge = extendTailwindMerge({
  extend: {
    classGroups: {
      'font-size': ['text-display', 'text-h1', 'text-h2', 'text-h3', 'text-h4', 'text-body', 'text-small', 'text-caption', 'text-label', 'text-kpi'],
      'text-color': [
        'text-app',
        'text-surface',
        'text-surface-secondary',
        'text-hover',
        'text-border-subtle',
        'text-border-strong',
        'text-text-primary',
        'text-text-secondary',
        'text-text-tertiary',
        'text-text-on-accent',
        'text-accent-50',
        'text-accent-400',
        'text-accent-500',
        'text-accent-600',
        'text-accent-700',
        'text-brand-panel',
        'text-ink',
        'text-ink-hover',
        'text-ink-text',
        'text-success-text',
        'text-success-bg',
        'text-warning-text',
        'text-warning-bg',
        'text-danger-text',
        'text-danger-bg',
        'text-info-text',
        'text-info-bg',
      ],
    },
  },
});

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}
