import React, { createContext, useState, ReactNode, useEffect, useContext } from 'react';
import { colors, shadows, radii, motion, zIndex } from './designTokens';

interface ThemeContextProps {
  isDark: boolean;
  toggleTheme: () => void;
  setTheme: (isDark: boolean) => void;
}

export const ThemeContext = createContext<ThemeContextProps>({
  isDark: true,
  toggleTheme: () => {},
  setTheme: () => {},
});

export const useTheme = () => useContext(ThemeContext);

export const ThemeProvider = ({ children }: { children: ReactNode }) => {
  const [isDark, setIsDark] = useState<boolean>(() => {
    const saved = localStorage.getItem('theme');
    if (saved) return saved === 'dark';
    return window.matchMedia('(prefers-color-scheme: dark)').matches;
  });

  useEffect(() => {
    const root = document.documentElement;
    const themeMode = isDark ? 'dark' : 'light';
    root.setAttribute('data-theme', themeMode);
    localStorage.setItem('theme', themeMode);

    const c = isDark ? colors.dark : colors.light;
    const s = isDark ? shadows.dark : shadows.light;

    const vars: Record<string, string> = {
      '--bg-app': c.bgApp,
      '--bg-surface': c.bgSurface,
      '--bg-surface-secondary': c.bgSurfaceSecondary,
      '--bg-hover': c.bgHover,
      '--border-subtle': c.borderSubtle,
      '--border-strong': c.borderStrong,
      '--text-primary': c.textPrimary,
      '--text-secondary': c.textSecondary,
      '--text-tertiary': c.textTertiary,
      '--text-on-accent': c.textOnAccent,
      '--accent-50': c.accent50,
      '--accent-400': c.accent400,
      '--accent-500': c.accent500,
      '--accent-600': c.accent600,
      '--accent-700': c.accent700,
      '--ink-bg': c.inkBg,
      '--ink-bg-hover': c.inkBgHover,
      '--ink-text': c.inkText,
      '--brand-panel-bg': c.brandPanelBg,
      '--ai-accent-from': c.aiAccentFrom,
      '--ai-accent-to': c.aiAccentTo,
      '--status-success-text': c.successText,
      '--status-success-bg': c.successBg,
      '--status-warning-text': c.warningText,
      '--status-warning-bg': c.warningBg,
      '--status-danger-text': c.dangerText,
      '--status-danger-bg': c.dangerBg,
      '--status-info-text': c.infoText,
      '--status-info-bg': c.infoBg,
      '--shadow-xs': s.xs,
      '--shadow-sm': s.sm,
      '--shadow-md': s.md,
      '--shadow-lg': s.lg,
      '--shadow-focus': s.focus,
      '--radius-sm': radii.sm,
      '--radius-md': radii.md,
      '--radius-lg': radii.lg,
      '--radius-xl': radii.xl,
      '--radius-2xl': radii['2xl'],
      '--radius-full': radii.full,
      '--motion-fast': motion.fast,
      '--motion-standard': motion.standard,
      '--motion-slow': motion.slow,
      '--motion-emphasis': motion.emphasis,
      '--z-dropdown': String(zIndex.dropdown),
      '--z-sticky': String(zIndex.sticky),
      '--z-overlay': String(zIndex.overlay),
      '--z-modal': String(zIndex.modal),
      '--z-popover': String(zIndex.popover),
      '--z-toast': String(zIndex.toast),
      '--z-tooltip': String(zIndex.tooltip),
    };

    for (const [key, value] of Object.entries(vars)) {
      root.style.setProperty(key, value);
    }
  }, [isDark]);

  const toggleTheme = () => setIsDark(prev => !prev);
  const setTheme = (val: boolean) => setIsDark(val);

  return (
    <ThemeContext.Provider value={{ isDark, toggleTheme, setTheme }}>
      {children}
    </ThemeContext.Provider>
  );
};
