import { Component, inject, input } from '@angular/core';
import { Icon, StorefrontService } from '@shop/shared';

/** The brand side of the sign-in and register pages (hidden on small screens). */
@Component({
  selector: 'buy-auth-panel',
  imports: [Icon],
  template: `
    <div class="glow" aria-hidden="true"></div>
    <p class="brand">{{ storefront.settings().store_name }}</p>
    <h2>{{ heading() }}</h2>
    <ul>
      <li><shr-icon name="package" /> Follow every order from your account</li>
      <li><shr-icon name="pin" /> Save addresses for a faster checkout</li>
      <li><shr-icon name="cash" /> Pay in cash when your order arrives</li>
    </ul>
  `,
  styles: `
    :host {
      position: relative;
      display: flex;
      flex-direction: column;
      justify-content: flex-end;
      gap: var(--space-4);
      padding: var(--space-10);
      overflow: hidden;
      isolation: isolate;
      border-radius: var(--radius-lg);
      color: var(--color-hero-text);
      background: linear-gradient(140deg, var(--color-hero-start), var(--color-hero-end));
    }
    .glow {
      position: absolute;
      inset: -30%;
      z-index: -1;
      background: radial-gradient(
        circle at 70% 20%,
        color-mix(in srgb, var(--color-accent) 40%, transparent),
        transparent 45%
      );
      animation: drift 16s var(--ease-in-out) infinite alternate;
    }
    @keyframes drift {
      to {
        transform: translate3d(-8%, 6%, 0);
      }
    }
    .brand {
      position: absolute;
      top: var(--space-10);
      left: var(--space-10);
      margin: 0;
      font-family: var(--font-display);
      font-size: 1.75rem;
      font-weight: 600;
    }
    h2 {
      margin: 0;
      font-family: var(--font-display);
      font-size: 2.5rem;
      font-weight: 500;
      line-height: 1.1;
    }
    ul {
      display: grid;
      gap: var(--space-3);
      margin: var(--space-4) 0 0;
      padding: 0;
      list-style: none;
      opacity: 0.9;
    }
    li {
      display: flex;
      align-items: center;
      gap: var(--space-3);
    }
    shr-icon {
      color: var(--color-accent);
    }
  `,
})
export class AuthPanel {
  readonly heading = input('Welcome back.');
  protected readonly storefront = inject(StorefrontService);
}
