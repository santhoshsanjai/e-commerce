/**
 * The colours staff can change in Admin → Storefront. Each `name` is a design token:
 * `primary` is the CSS variable `--color-primary`. Defaults live in shared/styles/_tokens.scss
 * (the only place colours are written down); the editor reads them from the page.
 */
export interface ThemeColor {
  name: string;
  label: string;
  hint?: string;
}

export interface ThemeColorGroup {
  title: string;
  colors: ThemeColor[];
}

export const THEME_COLOR_GROUPS: ThemeColorGroup[] = [
  {
    title: 'Brand',
    colors: [
      { name: 'primary', label: 'Primary', hint: 'Buttons, links and selected items' },
      { name: 'primary-contrast', label: 'Text on primary' },
      { name: 'accent', label: 'Accent', hint: 'Highlights, badges and small details' },
      { name: 'accent-contrast', label: 'Text on accent' },
    ],
  },
  {
    title: 'Page',
    colors: [
      { name: 'background', label: 'Page background' },
      { name: 'surface', label: 'Cards and panels' },
      { name: 'surface-alt', label: 'Soft sections', hint: 'Image wells, bands and hovers' },
      { name: 'text', label: 'Text' },
      { name: 'muted', label: 'Secondary text' },
      { name: 'border', label: 'Borders and dividers' },
    ],
  },
  {
    title: 'Header and footer',
    colors: [
      { name: 'announcement-bg', label: 'Trust bar' },
      { name: 'announcement-text', label: 'Trust bar text' },
      { name: 'header-bg', label: 'Header' },
      { name: 'header-text', label: 'Header text' },
      { name: 'footer-bg', label: 'Footer' },
      { name: 'footer-text', label: 'Footer text' },
    ],
  },
  {
    title: 'Home page hero',
    colors: [
      { name: 'hero-start', label: 'Hero gradient start' },
      { name: 'hero-end', label: 'Hero gradient end' },
      { name: 'hero-text', label: 'Hero text' },
    ],
  },
  {
    title: 'Status',
    colors: [
      { name: 'sale', label: 'Sale price and discount' },
      { name: 'success', label: 'Success' },
      { name: 'warning', label: 'Warning' },
      { name: 'danger', label: 'Error' },
    ],
  },
  {
    title: 'Admin portal',
    colors: [
      { name: 'sidebar-bg', label: 'Sidebar' },
      { name: 'sidebar-text', label: 'Sidebar text' },
    ],
  },
];

export const THEME_COLOR_NAMES: ReadonlySet<string> = new Set(
  THEME_COLOR_GROUPS.flatMap((g) => g.colors.map((c) => c.name)),
);

/** Ready-made palettes staff can start from. Only the colours listed change. */
export interface ThemePreset {
  name: string;
  colors: Record<string, string>;
}

export const THEME_PRESETS: ThemePreset[] = [
  { name: 'Navy & white (default)', colors: {} },
  {
    name: 'Emerald',
    colors: {
      primary: '#0f3d33',
      accent: '#1f8a6a',
      'surface-alt': '#eef5f2',
      border: '#dfe9e5',
      'announcement-bg': '#eef5f2',
      'announcement-text': '#0f3d33',
      'footer-bg': '#0f3d33',
      'hero-start': '#eef5f2',
      'hero-end': '#d5e8e0',
      'hero-text': '#0f3d33',
      'sidebar-bg': '#0f3d33',
    },
  },
  {
    name: 'Charcoal',
    colors: {
      primary: '#1f2328',
      accent: '#4b5563',
      'surface-alt': '#f3f4f6',
      border: '#e5e7eb',
      'announcement-bg': '#f3f4f6',
      'announcement-text': '#1f2328',
      'footer-bg': '#1f2328',
      'hero-start': '#f3f4f6',
      'hero-end': '#e2e4e8',
      'hero-text': '#1f2328',
      'sidebar-bg': '#1f2328',
    },
  },
  {
    name: 'Burgundy',
    colors: {
      primary: '#5a1a2b',
      accent: '#a8324f',
      'surface-alt': '#f8eff1',
      border: '#eee0e3',
      'announcement-bg': '#f8eff1',
      'announcement-text': '#5a1a2b',
      'footer-bg': '#5a1a2b',
      'hero-start': '#f8eff1',
      'hero-end': '#efd9de',
      'hero-text': '#5a1a2b',
      'sidebar-bg': '#5a1a2b',
    },
  },
  {
    name: 'Royal blue',
    colors: {
      primary: '#1f3b8f',
      accent: '#2f6fe0',
      'surface-alt': '#eef2fb',
      border: '#e1e6f2',
      'announcement-bg': '#eef2fb',
      'announcement-text': '#1f3b8f',
      'footer-bg': '#1f3b8f',
      'hero-start': '#eef2fb',
      'hero-end': '#d8e1f5',
      'hero-text': '#1f3b8f',
      'sidebar-bg': '#1f3b8f',
    },
  },
];
