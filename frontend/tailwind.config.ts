import type { Config } from 'tailwindcss';
import tailwindcssAnimate from 'tailwindcss-animate';

// Every color/radius/shadow/motion value here resolves through the CSS
// custom properties ThemeProvider.tsx sets on :root — so a Tailwind utility
// like `bg-surface` or `text-primary` automatically tracks light/dark theme
// switching without any dark: variant needed (06_UI/Design_Tokens.md).
export default {
  darkMode: ['class', '[data-theme="dark"]'],
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    screens: {
      xs: '375px',
      sm: '430px',
      md: '768px',
      lg: '1024px',
      xl: '1280px',
      '2xl': '1440px',
    },
    extend: {
      colors: {
        app: 'var(--bg-app)',
        surface: 'var(--bg-surface)',
        'surface-secondary': 'var(--bg-surface-secondary)',
        hover: 'var(--bg-hover)',
        border: {
          subtle: 'var(--border-subtle)',
          strong: 'var(--border-strong)',
        },
        text: {
          primary: 'var(--text-primary)',
          secondary: 'var(--text-secondary)',
          tertiary: 'var(--text-tertiary)',
          'on-accent': 'var(--text-on-accent)',
        },
        accent: {
          50: 'var(--accent-50)',
          400: 'var(--accent-400)',
          500: 'var(--accent-500)',
          600: 'var(--accent-600)',
          700: 'var(--accent-700)',
        },
        'brand-panel': 'var(--brand-panel-bg)',
        ink: {
          DEFAULT: 'var(--ink-bg)',
          hover: 'var(--ink-bg-hover)',
        },
        'ink-text': 'var(--ink-text)',
        success: { text: 'var(--status-success-text)', bg: 'var(--status-success-bg)' },
        warning: { text: 'var(--status-warning-text)', bg: 'var(--status-warning-bg)' },
        danger: { text: 'var(--status-danger-text)', bg: 'var(--status-danger-bg)' },
        info: { text: 'var(--status-info-text)', bg: 'var(--status-info-bg)' },
      },
      borderRadius: {
        none: 'var(--radius-none, 0px)',
        sm: 'var(--radius-sm)',
        DEFAULT: 'var(--radius-md)',
        md: 'var(--radius-md)',
        lg: 'var(--radius-lg)',
        xl: 'var(--radius-xl)',
        '2xl': 'var(--radius-2xl)',
        full: 'var(--radius-full)',
      },
      boxShadow: {
        xs: 'var(--shadow-xs)',
        sm: 'var(--shadow-sm)',
        md: 'var(--shadow-md)',
        lg: 'var(--shadow-lg)',
        focus: 'var(--shadow-focus)',
      },
      zIndex: {
        dropdown: 'var(--z-dropdown)',
        sticky: 'var(--z-sticky)',
        overlay: 'var(--z-overlay)',
        modal: 'var(--z-modal)',
        popover: 'var(--z-popover)',
        toast: 'var(--z-toast)',
        tooltip: 'var(--z-tooltip)',
      },
      fontFamily: {
        sans: ["'Inter'", '-apple-system', 'BlinkMacSystemFont', "'Segoe UI'", 'Roboto', 'sans-serif'],
        // Editorial serif reserved for hero/display headings only (brand
        // panels, page greetings) — never body text, labels, or data,
        // which stay on Inter for readability and density.
        display: ["'Playfair Display'", 'ui-serif', 'Georgia', 'serif'],
      },
      fontSize: {
        display: ['40px', { lineHeight: '48px', fontWeight: '600' }],
        h1: ['32px', { lineHeight: '40px', fontWeight: '600' }],
        h2: ['24px', { lineHeight: '32px', fontWeight: '600' }],
        h3: ['20px', { lineHeight: '28px', fontWeight: '600' }],
        h4: ['16px', { lineHeight: '24px', fontWeight: '600' }],
        body: ['14px', { lineHeight: '20px', fontWeight: '400' }],
        small: ['13px', { lineHeight: '18px', fontWeight: '400' }],
        caption: ['12px', { lineHeight: '16px', fontWeight: '500' }],
        label: ['12px', { lineHeight: '16px', fontWeight: '600', letterSpacing: '0.04em' }],
        kpi: ['32px', { lineHeight: '1.1', fontWeight: '600' }],
      },
      transitionDuration: {
        fast: '140ms',
        standard: '200ms',
        slow: '320ms',
        emphasis: '480ms',
      },
      transitionTimingFunction: {
        standard: 'cubic-bezier(0.4, 0, 0.2, 1)',
        emphasis: 'cubic-bezier(0.16, 1, 0.3, 1)',
      },
      keyframes: {
        'accordion-down': { from: { height: '0' }, to: { height: 'var(--radix-accordion-content-height)' } },
        'accordion-up': { from: { height: 'var(--radix-accordion-content-height)' }, to: { height: '0' } },
      },
      animation: {
        'accordion-down': 'accordion-down 200ms ease-out',
        'accordion-up': 'accordion-up 200ms ease-out',
      },
    },
  },
  plugins: [tailwindcssAnimate],
} satisfies Config;
