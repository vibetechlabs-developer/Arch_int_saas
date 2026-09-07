import type { Variants } from 'framer-motion';

// Design_Principles.md §5: staggered reveals reserved for meaningful
// groups only (a KPI strip, a timeline) — never an entire page on every
// load. 40–60ms stagger, motion-emphasis curve.
export const staggerContainer: Variants = {
  hidden: {},
  show: { transition: { staggerChildren: 0.05 } },
};

export const fadeInUp: Variants = {
  hidden: { opacity: 0, y: 8 },
  show: { opacity: 1, y: 0, transition: { duration: 0.48, ease: [0.16, 1, 0.3, 1] } },
};

// Responsive_Accessibility.md §4: with prefers-reduced-motion, decorative
// reveals are disabled entirely — this collapses to an instant opacity-only
// fade with no translate.
export const fadeInUpReduced: Variants = {
  hidden: { opacity: 0 },
  show: { opacity: 1, transition: { duration: 0.01 } },
};

// Route/page-level transition (Design_Principles.md §5): opacity + 4–8px
// translate only, motion-slow.
export const pageTransition: Variants = {
  hidden: { opacity: 0, y: 6 },
  show: { opacity: 1, y: 0, transition: { duration: 0.32, ease: [0.4, 0, 0.2, 1] } },
};

export const pageTransitionReduced: Variants = {
  hidden: { opacity: 0 },
  show: { opacity: 1, transition: { duration: 0.01 } },
};
