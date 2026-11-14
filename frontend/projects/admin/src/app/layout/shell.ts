import { Component, computed, inject, signal } from '@angular/core';
import { Router, RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';
import { AuthService } from '@shop/shared';
import { NAV_ITEMS } from '../navigation';

@Component({
  selector: 'adm-shell',
  imports: [RouterOutlet, RouterLink, RouterLinkActive],
  template: `
    <div class="shell" [class.collapsed]="collapsed()">
      <aside aria-label="Admin navigation">
        <div class="brand">{{ collapsed() ? 'A' : 'Admin portal' }}</div>
        <nav>
          @for (item of menu(); track item.path) {
            <a [routerLink]="item.path" routerLinkActive="active">{{ item.label }}</a>
          }
        </nav>
      </aside>
      <div class="main">
        <header>
          <button
            type="button"
            class="btn btn-secondary"
            (click)="collapsed.set(!collapsed())"
            [attr.aria-expanded]="!collapsed()"
          >
            <span class="visually-hidden">Toggle navigation</span>☰
          </button>
          <span class="spacer"></span>
          @if (auth.user(); as user) {
            <span class="who">{{ user.full_name }} · {{ user.roles.join(', ') }}</span>
          }
          <button type="button" class="btn btn-secondary" (click)="logout()">Sign out</button>
        </header>
        <main id="main" tabindex="-1">
          <router-outlet />
        </main>
      </div>
    </div>
  `,
  styles: `
    .shell {
      display: grid;
      grid-template-columns: 240px 1fr;
      min-height: 100vh;
    }
    .shell.collapsed {
      grid-template-columns: 64px 1fr;
    }
    .collapsed nav {
      display: none;
    }
    aside {
      background: var(--color-surface);
      border-right: 1px solid var(--color-border);
      padding: var(--space-4) var(--space-3);
    }
    .brand {
      font-weight: 700;
      color: var(--color-primary);
      padding: var(--space-2);
      margin-bottom: var(--space-4);
    }
    nav {
      display: flex;
      flex-direction: column;
      gap: var(--space-1);
    }
    nav a {
      padding: var(--space-2) var(--space-3);
      border-radius: var(--radius-md);
      color: var(--color-text);
      text-decoration: none;
    }
    nav a.active {
      background: color-mix(in srgb, var(--color-primary) 10%, transparent);
      color: var(--color-primary);
      font-weight: 600;
    }
    header {
      display: flex;
      align-items: center;
      gap: var(--space-3);
      padding: var(--space-3) var(--space-6);
      background: var(--color-surface);
      border-bottom: 1px solid var(--color-border);
    }
    .spacer {
      flex: 1;
    }
    .who {
      color: var(--color-muted);
      font-size: var(--font-size-sm);
    }
    main {
      padding: var(--space-6);
    }
    @media (max-width: 768px) {
      .shell,
      .shell.collapsed {
        grid-template-columns: 1fr;
      }
      .collapsed aside {
        display: none;
      }
      .who {
        display: none;
      }
    }
  `,
})
export class Shell {
  protected readonly auth = inject(AuthService);
  private readonly router = inject(Router);
  protected readonly collapsed = signal(false);
  protected readonly menu = computed(() => {
    const granted = this.auth.permissions();
    return NAV_ITEMS.filter((item) => granted.has(item.permission));
  });

  async logout(): Promise<void> {
    await this.auth.logout();
    await this.router.navigateByUrl('/login');
  }
}
