import { Component, computed, inject, signal } from '@angular/core';
import { NavigationEnd, Router, RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';
import { AuthService, Icon, StorefrontService } from '@shop/shared';
import { filter } from 'rxjs';
import { NAV_ITEMS } from '../navigation';

@Component({
  selector: 'adm-shell',
  imports: [RouterOutlet, RouterLink, RouterLinkActive, Icon],
  templateUrl: './shell.html',
  styleUrl: './shell.scss',
})
export class Shell {
  protected readonly auth = inject(AuthService);
  protected readonly storefront = inject(StorefrontService);
  private readonly router = inject(Router);
  /** Desktop: narrow icon rail. Phone: the menu is a drawer, closed unless opened. */
  protected readonly collapsed = signal(false);
  protected readonly drawerOpen = signal(false);
  protected readonly menu = computed(() => {
    const granted = this.auth.permissions();
    return NAV_ITEMS.filter((item) => granted.has(item.permission));
  });
  protected readonly initials = computed(() =>
    (this.auth.user()?.full_name ?? '')
      .split(/\s+/)
      .filter(Boolean)
      .slice(0, 2)
      .map((part) => part[0].toUpperCase())
      .join(''),
  );

  constructor() {
    this.router.events
      .pipe(filter((e) => e instanceof NavigationEnd))
      .subscribe(() => this.drawerOpen.set(false));
  }

  protected toggle(): void {
    if (matchMedia('(max-width: 768px)').matches) {
      this.drawerOpen.set(!this.drawerOpen());
    } else {
      this.collapsed.set(!this.collapsed());
    }
  }

  async logout(): Promise<void> {
    await this.auth.logout();
    await this.router.navigateByUrl('/login');
  }
}
