import { Component, inject } from '@angular/core';
import { Router, RouterLink } from '@angular/router';
import { AuthService } from '@shop/shared';
import { CartStore } from '../features/cart/cart.store';

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
          <a routerLink="/orders">Orders</a>
          <a routerLink="/account">Account</a>
          <a
            routerLink="/cart"
            class="cart"
            [attr.aria-label]="'Cart, ' + cart.count() + (cart.count() === 1 ? ' item' : ' items')"
          >
            Cart
            @if (cart.count()) {
              <span class="count" aria-hidden="true">{{ cart.count() }}</span>
            }
          </a>
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
    nav .btn {
      white-space: nowrap;
    }
    @media (max-width: 420px) {
      nav {
        gap: var(--space-3);
      }
    }
    .brand {
      font-weight: 700;
      font-size: var(--font-size-lg);
      text-decoration: none;
      color: var(--color-primary);
    }
    .cart {
      display: inline-flex;
      align-items: center;
      gap: var(--space-1);
    }
    .count {
      min-width: 20px;
      padding: 0 6px;
      border-radius: 999px;
      background: var(--color-secondary);
      color: var(--color-secondary-contrast);
      font-size: var(--font-size-sm);
      font-weight: 700;
      text-align: center;
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
  protected readonly cart = inject(CartStore);
  private readonly router = inject(Router);

  async logout(): Promise<void> {
    await this.auth.logout();
    await this.router.navigateByUrl('/');
  }
}
