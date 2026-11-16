import { HttpClient } from '@angular/common/http';
import { DOCUMENT, inject, Injectable, signal } from '@angular/core';
import { firstValueFrom } from 'rxjs';
import { API_BASE_URL } from '../api/api-config';
import { THEME_COLOR_NAMES } from './theme-colors';

export interface Storefront {
  store_name: string;
  announcement: string;
  colors: Record<string, string>;
}

const DEFAULT: Storefront = { store_name: 'Shop', announcement: '', colors: {} };
const CACHE_KEY = 'storefront';
const HEX = /^#[0-9a-f]{6}$/i;

/**
 * The shop's name, announcement and colours, set by staff in Admin → Storefront.
 *
 * Colours are applied as CSS variables on <html>, over the defaults in _tokens.scss. The last
 * settings are kept in localStorage so a returning visitor sees the right colours on first paint.
 */
@Injectable({ providedIn: 'root' })
export class StorefrontService {
  private readonly http = inject(HttpClient);
  private readonly base = inject(API_BASE_URL);
  private readonly root = inject(DOCUMENT).documentElement;

  private readonly state = signal<Storefront>(readCache() ?? DEFAULT);
  readonly settings = this.state.asReadonly();
  private applied = new Set<string>();

  constructor() {
    this.apply(this.state().colors);
  }

  /** Called at start-up. Never fails: the defaults stay in place if the API is unreachable. */
  async load(): Promise<void> {
    try {
      this.set(await firstValueFrom(this.http.get<Storefront>(`${this.base}/storefront`)));
    } catch {
      // Keep the cached or default look.
    }
  }

  /** Use these settings now (after saving, or to preview colours while editing). */
  set(settings: Storefront, persist = true): void {
    this.state.set(settings);
    this.apply(settings.colors);
    if (persist) writeCache(settings);
  }

  /** The value a colour has with no override: the default from _tokens.scss. */
  defaultColor(name: string): string {
    const override = this.root.style.getPropertyValue(`--color-${name}`);
    this.root.style.removeProperty(`--color-${name}`);
    const value = getComputedStyle(this.root).getPropertyValue(`--color-${name}`).trim();
    if (override) this.root.style.setProperty(`--color-${name}`, override);
    return value;
  }

  private apply(colors: Record<string, string>): void {
    for (const name of this.applied) {
      if (!(name in colors)) this.root.style.removeProperty(`--color-${name}`);
    }
    this.applied = new Set();
    for (const [name, value] of Object.entries(colors)) {
      // Only known tokens and plain hex colours ever reach the page's styles.
      if (THEME_COLOR_NAMES.has(name) && HEX.test(value)) {
        this.root.style.setProperty(`--color-${name}`, value);
        this.applied.add(name);
      }
    }
  }
}

function readCache(): Storefront | null {
  try {
    const raw = localStorage.getItem(CACHE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as Storefront;
    return typeof parsed.store_name === 'string' && typeof parsed.colors === 'object'
      ? { ...DEFAULT, ...parsed }
      : null;
  } catch {
    return null;
  }
}

function writeCache(settings: Storefront): void {
  try {
    localStorage.setItem(CACHE_KEY, JSON.stringify(settings));
  } catch {
    // Private mode or storage full: the API still provides the settings.
  }
}
