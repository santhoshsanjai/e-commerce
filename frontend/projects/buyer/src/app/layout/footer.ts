import { Component, inject } from '@angular/core';
import { RouterLink } from '@angular/router';
import { AuthService, Icon, StorefrontService } from '@shop/shared';

@Component({
  selector: 'buy-footer',
  imports: [RouterLink, Icon],
  template: `
    <footer>
      <div class="promises container">
        <div><shr-icon name="cash" /><span>Cash on delivery</span></div>
        <div><shr-icon name="truck" /><span>Tracked delivery</span></div>
        <div><shr-icon name="lock" /><span>Secure accounts</span></div>
        <div><shr-icon name="tag" /><span>Prices include taxes</span></div>
      </div>
      <div class="cols container">
        <div class="about">
          <p class="brand">{{ storefront.settings().store_name }}</p>
          <p>
            A considered collection, chosen with care and delivered to your door. Pay when your
            order arrives.
          </p>
        </div>
        <nav aria-label="Shop">
          <p class="title">Shop</p>
          <a routerLink="/shop" [queryParams]="{ sort: 'newest' }">New in</a>
          <a routerLink="/shop">All products</a>
          <a routerLink="/shop" [queryParams]="{ sort: 'price_asc' }">Best value</a>
        </nav>
        <nav aria-label="Your account">
          <p class="title">Your account</p>
          @if (auth.user()) {
            <a routerLink="/account">Account details</a>
            <a routerLink="/orders">Order history</a>
            <a routerLink="/cart">Cart</a>
          } @else {
            <a routerLink="/login">Sign in</a>
            <a routerLink="/register">Register</a>
            <a routerLink="/forgot-password">Reset password</a>
          }
        </nav>
      </div>
      <div class="legal container">
        <p>&copy; {{ year }} {{ storefront.settings().store_name }}. All rights reserved.</p>
        <p>Pay on delivery · Tracked shipping</p>
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
    .promises {
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: var(--space-4);
      padding-block: var(--space-8);
      border-bottom: 1px solid color-mix(in srgb, var(--color-footer-text) 14%, transparent);
      div {
        display: flex;
        align-items: center;
        justify-content: center;
        gap: var(--space-3);
        letter-spacing: 0.04em;
        --icon-size: 22px;
      }
      shr-icon {
        color: var(--color-accent);
      }
    }
    .cols {
      display: grid;
      grid-template-columns: 2fr 1fr 1fr;
      gap: var(--space-10);
      padding-block: var(--space-12);
    }
    .brand {
      margin: 0 0 var(--space-3);
      font-family: var(--font-display);
      font-size: 2rem;
      font-weight: 600;
      line-height: 1;
      color: var(--color-footer-text);
    }
    .about p:not(.brand) {
      max-width: 36ch;
      margin: 0;
      opacity: 0.8;
      line-height: 1.7;
    }
    nav {
      display: flex;
      flex-direction: column;
      gap: var(--space-2);
    }
    .title {
      margin: 0 0 var(--space-2);
      font-size: var(--font-size-xs);
      font-weight: 600;
      letter-spacing: var(--tracking-wide);
      text-transform: uppercase;
      color: var(--color-accent);
    }
    nav a {
      align-self: flex-start;
      color: inherit;
      opacity: 0.85;
      text-decoration: none;
      transition:
        opacity var(--duration-fast) ease,
        transform var(--duration-fast) var(--ease-out);
    }
    nav a:hover {
      opacity: 1;
      transform: translateX(3px);
    }
    .legal {
      display: flex;
      flex-wrap: wrap;
      justify-content: space-between;
      gap: var(--space-2);
      padding-block: var(--space-5);
      border-top: 1px solid color-mix(in srgb, var(--color-footer-text) 14%, transparent);
      font-size: var(--font-size-xs);
      opacity: 0.7;
      p {
        margin: 0;
      }
    }
    @media (max-width: 768px) {
      .promises {
        grid-template-columns: repeat(2, 1fr);
        div {
          justify-content: flex-start;
        }
      }
      .cols {
        grid-template-columns: 1fr 1fr;
        gap: var(--space-8);
      }
      .about {
        grid-column: 1 / -1;
      }
    }
  `,
})
export class Footer {
  protected readonly storefront = inject(StorefrontService);
  protected readonly auth = inject(AuthService);
  protected readonly year = new Date().getFullYear();
}
