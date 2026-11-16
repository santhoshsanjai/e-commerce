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
      { name: 'announcement-bg', label: 'Announcement bar' },
      { name: 'announcement-text', label: 'Announcement text' },
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
  { name: 'Ink & brass (default)', colors: {} },
  {
    name: 'Emerald',
    colors: {
      primary: '#0f3d33',
      accent: '#c2a36b',
      background: '#f7f6f2',
      'surface-alt': '#ecebe4',
      border: '#e1dfd6',
      'announcement-bg': '#0f3d33',
      'footer-bg': '#0b2a24',
      'hero-start': '#0f3d33',
      'hero-end': '#2c5c50',
      'sidebar-bg': '#0b2a24',
    },
  },
  {
    name: 'Noir',
    colors: {
      primary: '#111111',
      accent: '#9a7b4f',
      background: '#f6f5f3',
      'surface-alt': '#ecebe8',
      border: '#e2e0dc',
      'announcement-bg': '#111111',
      'footer-bg': '#0c0c0c',
      'hero-start': '#141414',
      'hero-end': '#3a3a3a',
      'sidebar-bg': '#0c0c0c',
    },
  },
  {
    name: 'Burgundy',
    colors: {
      primary: '#5a1a2b',
      accent: '#c09a5b',
      background: '#fbf7f4',
      'surface-alt': '#f3ebe6',
      border: '#eadfd8',
      'announcement-bg': '#5a1a2b',
      'footer-bg': '#2e0f17',
      'hero-start': '#5a1a2b',
      'hero-end': '#8a3a4c',
      'sidebar-bg': '#2e0f17',
    },
  },
  {
    name: 'Royal blue',
    colors: {
      primary: '#1f3b8f',
      accent: '#e0a43b',
      'accent-contrast': '#1b1e23',
      background: '#f6f7fb',
      'surface-alt': '#eceff7',
      border: '#e1e5ef',
      'announcement-bg': '#1f3b8f',
      'footer-bg': '#121f47',
      'hero-start': '#1f3b8f',
      'hero-end': '#3d5fc4',
      'sidebar-bg': '#121f47',
    },
  },
];
