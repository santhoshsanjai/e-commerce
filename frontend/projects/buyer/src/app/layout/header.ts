import { Component, computed, effect, HostListener, inject, signal } from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';
import { NavigationEnd, Router, RouterLink, RouterLinkActive } from '@angular/router';
import { AuthService, Icon, StorefrontService } from '@shop/shared';
import { filter } from 'rxjs';
import { CartStore } from '../features/cart/cart.store';
import { CatalogApi } from '../features/catalog/catalog.api';

@Component({
  selector: 'buy-header',
  imports: [RouterLink, RouterLinkActive, Icon],
  templateUrl: './header.html',
  styleUrl: './header.scss',
})
export class Header {
  protected readonly auth = inject(AuthService);
  protected readonly cart = inject(CartStore);
  protected readonly storefront = inject(StorefrontService);
  private readonly router = inject(Router);

  private readonly categories = toSignal(inject(CatalogApi).categories(), { initialValue: [] });
  protected readonly topCategories = computed(() =>
    this.categories()
      .filter((c) => !c.parent_id)
      .slice(0, 8),
  );
  /** Categories shown inline in the desktop header; the rest are one click away in the shop. */
  protected readonly navCategories = computed(() => this.topCategories().slice(0, 3));
  /** Text staff set in Admin → Storefront replaces the standard trust points. */
  protected readonly customAnnouncement = computed(() =>
    this.storefront.settings().announcement?.trim(),
  );

  protected readonly scrolled = signal(false);
  protected readonly menuOpen = signal(false);
  protected readonly bump = signal(false);

  constructor() {
    this.router.events
      .pipe(filter((e) => e instanceof NavigationEnd))
      .subscribe(() => this.menuOpen.set(false));

    // A little pop on the bag icon whenever the item count goes up.
    let last = this.cart.count();
    effect(() => {
      const count = this.cart.count();
      if (count > last) {
        this.bump.set(false);
        requestAnimationFrame(() => this.bump.set(true));
      }
      last = count;
    });
  }

  @HostListener('window:scroll')
  protected onScroll(): void {
    this.scrolled.set(window.scrollY > 8);
  }

  @HostListener('document:keydown.escape')
  protected onEscape(): void {
    this.menuOpen.set(false);
  }

  protected search(term: string): void {
    void this.router.navigate(['/shop'], { queryParams: { q: term.trim() || null } });
  }

  async logout(): Promise<void> {
    this.menuOpen.set(false);
    await this.auth.logout();
    await this.router.navigateByUrl('/');
  }
}
