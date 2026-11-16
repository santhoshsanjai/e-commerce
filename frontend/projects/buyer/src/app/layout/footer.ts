import { Component, inject } from '@angular/core';
import { RouterLink } from '@angular/router';
import { AuthService, StorefrontService } from '@shop/shared';

@Component({
  selector: 'buy-footer',
  imports: [RouterLink],
  template: `
    <footer>
      <div class="row container">
        <nav aria-label="Footer">
          <a routerLink="/shop" [queryParams]="{ sort: 'newest' }">New in</a>
          <a routerLink="/shop">All products</a>
          @if (auth.user()) {
            <a routerLink="/account">My account</a>
            <a routerLink="/orders">My orders</a>
          } @else {
            <a routerLink="/login">Sign in</a>
            <a routerLink="/register">Create account</a>
          }
          <a routerLink="/cart">Cart</a>
        </nav>
      </div>
      <div class="legal container">
        <p>&copy; {{ year }} {{ storefront.settings().store_name }}. All rights reserved.</p>
        <p>Cash on delivery · Tracked delivery</p>
      </div>
    </footer>
  `,
  styles: `
    footer {
      margin-top: auto;
      background: var(--color-footer-bg);
      color: var(--color-footer-text);
      font-size: var(--font-size-sm);
    }
    .row {
      padding-block: var(--space-8);
    }
    nav {
      display: flex;
      flex-wrap: wrap;
      justify-content: center;
      gap: var(--space-3) var(--space-10);
    }
    nav a {
      color: inherit;
      font-weight: var(--font-weight-medium);
      text-decoration: none;
      opacity: 0.9;
      transition: opacity var(--duration-fast) ease;
    }
    nav a:hover {
      opacity: 1;
      text-decoration: underline;
    }
    .legal {
      display: flex;
      flex-wrap: wrap;
      justify-content: space-between;
      gap: var(--space-2);
      padding-block: var(--space-4);
      border-top: 1px solid color-mix(in srgb, var(--color-footer-text) 18%, transparent);
      font-size: var(--font-size-xs);
      opacity: 0.75;
      p {
        margin: 0;
      }
    }
    @media (max-width: 560px) {
      nav {
        justify-content: flex-start;
        gap: var(--space-3) var(--space-6);
      }
    }
  `,
})
export class Footer {
  protected readonly storefront = inject(StorefrontService);
  protected readonly auth = inject(AuthService);
  protected readonly year = new Date().getFullYear();
}
