import { HttpClient } from '@angular/common/http';
import { Component, computed, inject, OnDestroy, OnInit, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import {
  API_BASE_URL,
  apiErrorMessage,
  Icon,
  Storefront,
  StorefrontService,
  THEME_COLOR_GROUPS,
  THEME_PRESETS,
  ThemePreset,
} from '@shop/shared';
import { firstValueFrom } from 'rxjs';

const HEX = /^#[0-9a-f]{6}$/i;

/**
 * Shop name, announcement bar and every colour of both apps. Changes preview live across the
 * admin portal and reach the shop once saved.
 */
@Component({
  selector: 'adm-storefront-page',
  imports: [FormsModule, Icon],
  templateUrl: './storefront-page.html',
  styleUrl: './storefront-page.scss',
})
export class StorefrontPage implements OnInit, OnDestroy {
  private readonly http = inject(HttpClient);
  private readonly url = `${inject(API_BASE_URL)}/admin/storefront`;
  private readonly storefront = inject(StorefrontService);

  protected readonly groups = THEME_COLOR_GROUPS;
  protected readonly presets = THEME_PRESETS;

  protected readonly loading = signal(true);
  protected readonly saving = signal(false);
  protected readonly notice = signal<string | null>(null);
  protected readonly error = signal<string | null>(null);

  protected readonly storeName = signal('');
  protected readonly announcement = signal('');
  /** Overrides only; a colour missing here uses the default from the design tokens. */
  protected readonly colors = signal<Record<string, string>>({});
  private readonly saved = signal<Storefront | null>(null);
  private defaults: Record<string, string> = {};

  protected readonly dirty = computed(() => {
    const s = this.saved();
    if (!s) return false;
    return (
      s.store_name !== this.storeName().trim() ||
      s.announcement !== this.announcement().trim() ||
      JSON.stringify(sorted(s.colors)) !== JSON.stringify(sorted(this.colors()))
    );
  });
  protected readonly overrideCount = computed(() => Object.keys(this.colors()).length);

  async ngOnInit(): Promise<void> {
    try {
      const current = await firstValueFrom(this.http.get<Storefront>(this.url));
      // Read the defaults with no overrides applied, then put the saved look back.
      this.storefront.set({ ...current, colors: {} }, false);
      for (const group of this.groups) {
        for (const c of group.colors)
          this.defaults[c.name] = toHex(this.storefront.defaultColor(c.name));
      }
      this.accept(current);
    } catch (err) {
      this.error.set(apiErrorMessage(err));
    } finally {
      this.loading.set(false);
    }
  }

  ngOnDestroy(): void {
    // Leaving without saving: drop the preview.
    const saved = this.saved();
    if (saved) this.storefront.set(saved);
  }

  protected value(name: string): string {
    return this.colors()[name] ?? this.defaults[name] ?? '#000000';
  }

  /** What a palette would set a colour to: its own value, else the default. */
  protected presetValue(preset: ThemePreset, name: string): string {
    return preset.colors[name] ?? this.defaults[name] ?? '#000000';
  }

  protected isOverridden(name: string): boolean {
    return name in this.colors();
  }

  protected setColor(name: string, value: string): void {
    const v = value.trim().toLowerCase();
    if (!HEX.test(v)) return;
    const next = { ...this.colors() };
    if (v === this.defaults[name]) delete next[name];
    else next[name] = v;
    this.colors.set(next);
    this.preview();
  }

  protected resetColor(name: string): void {
    const next = { ...this.colors() };
    delete next[name];
    this.colors.set(next);
    this.preview();
  }

  protected applyPreset(preset: ThemePreset): void {
    this.colors.set({ ...preset.colors });
    this.preview();
  }

  protected resetAll(): void {
    this.colors.set({});
    this.preview();
  }

  protected discard(): void {
    const saved = this.saved();
    if (saved) this.accept(saved);
  }

  protected async save(): Promise<void> {
    this.saving.set(true);
    this.notice.set(null);
    this.error.set(null);
    try {
      const body = {
        store_name: this.storeName().trim(),
        announcement: this.announcement().trim(),
        colors: this.colors(),
      };
      this.accept(await firstValueFrom(this.http.put<Storefront>(this.url, body)));
      this.notice.set('Saved. Visitors see the new look the next time they open the shop.');
    } catch (err) {
      this.error.set(apiErrorMessage(err));
    } finally {
      this.saving.set(false);
    }
  }

  private accept(s: Storefront): void {
    this.saved.set(s);
    this.storeName.set(s.store_name);
    this.announcement.set(s.announcement);
    this.colors.set({ ...s.colors });
    this.storefront.set(s);
  }

  protected preview(): void {
    this.storefront.set(
      {
        store_name: this.storeName().trim() || this.saved()?.store_name || 'Shop',
        announcement: this.announcement(),
        colors: this.colors(),
      },
      false,
    );
  }
}

function sorted(map: Record<string, string>): [string, string][] {
  return Object.entries(map).sort(([a], [b]) => a.localeCompare(b));
}

/** Computed styles may come back as rgb(); colour inputs need #rrggbb. */
function toHex(value: string): string {
  if (HEX.test(value)) return value.toLowerCase();
  const m = value.match(/rgba?\(\s*(\d+)[,\s]+(\d+)[,\s]+(\d+)/);
  if (!m) return '#000000';
  return (
    '#' +
    m
      .slice(1, 4)
      .map((n) => Number(n).toString(16).padStart(2, '0'))
      .join('')
  );
}
