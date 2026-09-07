import { useEffect, useRef, useState } from 'react';

const EASE_OUT_EXPO = (t: number) => (t === 1 ? 1 : 1 - Math.pow(2, -10 * t));

/**
 * Animates a number from 0 to `target` once on mount — the KPI "count-up"
 * cue Design_Principles.md §5 calls out as the emphasis-tier reveal that
 * signals "these numbers just loaded together." Respects
 * prefers-reduced-motion by snapping straight to the final value.
 */
export function useCountUp(target: number, durationMs = 700): number {
  const [value, setValue] = useState(0);
  const targetRef = useRef(target);
  targetRef.current = target;

  useEffect(() => {
    const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    if (prefersReducedMotion) {
      setValue(targetRef.current);
      return;
    }

    let frame: number;
    const start = performance.now();
    const from = 0;
    const to = targetRef.current;

    function tick(now: number) {
      const elapsed = now - start;
      const progress = Math.min(elapsed / durationMs, 1);
      setValue(from + (to - from) * EASE_OUT_EXPO(progress));
      if (progress < 1) frame = requestAnimationFrame(tick);
    }

    frame = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frame);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [target, durationMs]);

  return value;
}
