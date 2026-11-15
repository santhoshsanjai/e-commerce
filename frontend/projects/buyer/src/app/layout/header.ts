import { Component, inject } from '@angular/core';
import { Router, RouterLink } from '@angular/router';
import { AuthService } from '@shop/shared';

@Component({
  selector: 'buy-header',
  imports: [RouterLink],
  template: `
    <header>
      <nav aria-label="Main">
        <a routerLink="/" class="brand">Shop</a>
        <span class="spacer"></span>
        @if (auth.user(); as user) {
          <span class="greeting">Hi, {{ user.full_name }}</span>
          <button type="button" class="btn btn-secondary" (click)="logout()">Sign out</button>
        } @else {
          <a routerLink="/login">Sign in</a>
          <a routerLink="/register" class="btn">Create account</a>
        }
      </nav>
    </header>
  `,
  styles: `
    header {
      background: var(--color-surface);
      border-bottom: 1px solid var(--color-border);
    }
    nav {
      display: flex;
      align-items: center;
      gap: var(--space-4);
      max-width: 1200px;
      margin: 0 auto;
      padding: var(--space-3) var(--space-4);
    }
    .brand {
      font-weight: 700;
      font-size: var(--font-size-lg);
      text-decoration: none;
      color: var(--color-primary);
    }
    .spacer {
      flex: 1;
    }
    .btn {
      text-decoration: none;
    }
    @media (max-width: 480px) {
      .greeting {
        display: none;
      }
    }
  `,
})
export class Header {
  protected readonly auth = inject(AuthService);
  private readonly router = inject(Router);

  async logout(): Promise<void> {
    await this.auth.logout();
    await this.router.navigateByUrl('/');
  }
}
