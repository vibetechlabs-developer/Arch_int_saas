import type { LucideIcon } from 'lucide-react';
import { Activity } from 'lucide-react';
import { motion, useReducedMotion } from 'framer-motion';
import { cn } from '@/lib/utils';
import { fadeInUp, fadeInUpReduced, staggerContainer } from '@/lib/motion';

export interface TimelineEntry {
  id: string;
  icon?: LucideIcon;
  title: string;
  meta: string;
}

// Component_Inventory.md §14: vertical connected-line, small icons, no
// large colorful bubbles. Design_Principles.md §5 explicitly names "a
// timeline" alongside the KPI strip as a sanctioned staggered-reveal group.
export function Timeline({ entries }: { entries: TimelineEntry[] }) {
  const shouldReduceMotion = useReducedMotion();
  const itemVariants = shouldReduceMotion ? fadeInUpReduced : fadeInUp;

  return (
    <motion.ol variants={staggerContainer} initial="hidden" animate="show" className="flex flex-col">
      {entries.map((entry, index) => {
        const Icon = entry.icon ?? Activity;
        const isLast = index === entries.length - 1;
        return (
          <motion.li key={entry.id} variants={itemVariants} className="relative flex gap-3 pb-5 last:pb-0">
            {!isLast && (
              <span className="absolute left-[11px] top-6 h-[calc(100%-1.25rem)] w-px bg-border-subtle" aria-hidden />
            )}
            <span
              className={cn(
                'flex size-6 shrink-0 items-center justify-center rounded-full border border-border-subtle bg-surface-secondary text-text-tertiary',
              )}
            >
              <Icon className="size-3.5" />
            </span>
            <div className="flex flex-col gap-0.5 pt-0.5">
              <p className="text-small text-text-primary">{entry.title}</p>
              <p className="text-caption text-text-tertiary">{entry.meta}</p>
            </div>
          </motion.li>
        );
      })}
    </motion.ol>
  );
}
