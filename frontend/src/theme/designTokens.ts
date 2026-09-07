// Design tokens for the "Architectural Warmth" visual identity: warm
// stone/ivory neutrals, a restrained muted-bronze accent (used sparingly —
// active indicators, links, small highlights), and dark graphite/ivory as
// the primary-action color (buttons), per the client-directed redesign
// brief. Structure (light/dark, accent50-700, status colors) is unchanged
// from the prior palette so every component that already consumes these
// semantic names re-themes automatically — only the values changed.

export const colors = {
  // Light Mode Semantics
  light: {
    bgApp: '#F5F3EE',
    bgSurface: '#FFFFFF',
    bgSurfaceSecondary: '#EFEBE3',
    bgHover: '#E8E2D6',
    borderSubtle: '#DDD8CF',
    borderStrong: '#CBC3B3',
    textPrimary: '#252422',
    textSecondary: '#6F6B64',
    textTertiary: '#969188',
    textOnAccent: '#FFFFFF',
    // Muted bronze — reserved for small, meaningful highlights (active nav
    // indicator, links, focus ring) per the brief's own button spec:
    // primary actions use `ink`, not this.
    accent50: '#F2EAD9',
    accent400: '#B99A6C',
    accent500: '#A4855A',
    accent600: '#8A6D46',
    accent700: '#6E5636',
    // Dark graphite — the primary-action color (buttons), distinct from
    // the bronze accent so "premium" isn't read as "everything is bronze."
    inkBg: '#282724',
    inkBgHover: '#3A3833',
    inkText: '#F7F5F0',
    successText: '#5B7052',
    successBg: '#E8EDE2',
    warningText: '#92661F',
    warningBg: '#F3E8D2',
    dangerText: '#9C4A3A',
    dangerBg: '#F5E3DE',
    infoText: '#4E6A80',
    infoBg: '#E4EBEF',
    // Full-bleed brand panels (auth/marketing) — deep graphite, not bronze;
    // a solid bronze fill at this scale would read as gaudy, not premium.
    brandPanelBg: '#211F1B',
    // AI Surface Accent (§1.7) — reserved for Phase 5, unused in the MVP.
    aiAccentFrom: '#282724',
    aiAccentTo: '#A4855A',
  },

  // Dark Mode Semantics (a warm "evening" surface, not an inverted light theme)
  dark: {
    bgApp: '#1C1B18',
    bgSurface: '#242320',
    bgSurfaceSecondary: '#2A2825',
    bgHover: '#332F2A',
    borderSubtle: '#3A3733',
    borderStrong: '#4A463F',
    textPrimary: '#F2EFE9',
    textSecondary: '#B5AFA3',
    textTertiary: '#837D71',
    textOnAccent: '#211F1B',
    accent50: '#332A1C',
    accent400: '#D2B583',
    accent500: '#C9A876',
    accent600: '#B4915F',
    accent700: '#8F734A',
    // In dark mode a dark-on-dark button would have no pop, so the primary
    // action inverts to a confident warm ivory fill — bronze stays the
    // *restrained* accent (nav indicator, links), never the loud button
    // color, in either theme.
    inkBg: '#EDE7DA',
    inkBgHover: '#DCD4C2',
    inkText: '#211F1B',
    successText: '#9CB68C',
    successBg: '#232821',
    warningText: '#D9AE6B',
    warningBg: '#332A19',
    dangerText: '#D98A78',
    dangerBg: '#34211C',
    infoText: '#8FB0C4',
    infoBg: '#1C2A31',
    brandPanelBg: '#151412',
    aiAccentFrom: '#EDE7DA',
    aiAccentTo: '#C9A876',
  },
};

export const spacing = {
  space1: '4px',
  space2: '8px',
  space3: '12px',
  space4: '16px',
  space5: '20px',
  space6: '24px',
  space8: '32px',
  space10: '40px',
  space12: '48px',
  space16: '64px',
  space20: '80px',
  space24: '96px',
};

export const radii = {
  none: '0px',
  sm: '4px',
  md: '6px',
  lg: '8px',
  xl: '12px',
  '2xl': '16px',
  full: '9999px',
};

// Dark-mode shadows are ~40% the opacity of their light-mode counterpart —
// elevation in dark mode reads primarily through surface-color steps,
// shadows are reserved for true overlays.
export const shadows = {
  light: {
    xs: '0 1px 2px rgba(37,36,34,0.05)',
    sm: '0 1px 3px rgba(37,36,34,0.07), 0 1px 2px rgba(37,36,34,0.05)',
    md: '0 4px 8px rgba(37,36,34,0.07), 0 2px 4px rgba(37,36,34,0.05)',
    lg: '0 12px 24px rgba(37,36,34,0.10), 0 4px 8px rgba(37,36,34,0.05)',
    focus: '0 0 0 3px rgba(164,133,90,0.35)',
  },
  dark: {
    xs: '0 1px 2px rgba(0,0,0,0.25)',
    sm: '0 1px 3px rgba(0,0,0,0.35)',
    md: '0 4px 8px rgba(0,0,0,0.4)',
    lg: '0 12px 24px rgba(0,0,0,0.55)',
    focus: '0 0 0 3px rgba(201,168,118,0.4)',
  },
};

export const motion = {
  instant: '0ms',
  fast: '140ms cubic-bezier(0.4, 0, 0.2, 1)',
  standard: '200ms cubic-bezier(0.4, 0, 0.2, 1)',
  slow: '320ms cubic-bezier(0.16, 1, 0.3, 1)',
  emphasis: '480ms cubic-bezier(0.16, 1, 0.3, 1)',
};

export const typography = {
  fontFamily: "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
  tabularNums: "'Inter', -apple-system, BlinkMacSystemFont, monospace",
};

// Z-Index Scale
export const zIndex = {
  base: 0,
  dropdown: 1000,
  sticky: 1100,
  overlay: 1200,
  modal: 1300,
  popover: 1400,
  toast: 1500,
  tooltip: 1600,
};

// Interactive-state notes, not values to port as CSS vars but behavior
// every component must follow:
// - disabled: 40% opacity, cursor:not-allowed, pointer-events:none on the
//   control itself, but its wrapper element stays hit-testable so a tooltip
//   explaining *why* it's disabled can still appear on hover/focus.
// - active/pressed: scale 98% + darken fill, motion-instant→fast.
