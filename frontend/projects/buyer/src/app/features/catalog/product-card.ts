import { Component, computed, inject, input, signal } from '@angular/core';
import { Router, RouterLink } from '@angular/router';
import { apiErrorMessage, AuthService, Icon, MoneyPipe, ProductCard as Card } from '@shop/shared';
import { CartStore } from '../cart/cart.store';
import { productLink } from './product-link';

@Component({
  selector: 'buy-product-card',
  imports: [RouterLink, MoneyPipe, Icon],
  template: `
    @let p = product();
    <a class="card-link" [routerLink]="link()" (click)="morph($event)">
      <div class="image">
        @if (p.image_url) {
          <img [src]="p.image_url" [alt]="p.image_alt" loading="lazy" />
        } @else {
          <div class="placeholder" aria-hidden="true"><shr-icon name="image" /></div>
        }
        @if (p.availability === 'OUT_OF_STOCK') {
          <span class="badge sold">Sold out</span>
        } @else if (discount(); as d) {
          <span class="badge sale">−{{ d }}%</span>
        } @else if (p.availability === 'LOW_STOCK') {
          <span class="badge low">Only a few left</span>
        }
      </div>
      <div class="body">
        <h3>{{ p.name }}</h3>
        @if (p.short_description) {
          <p class="short">{{ p.short_description }}</p>
        }
        <div class="foot">
          <p class="price">
            <span [class.now]="p.compare_at_minor">{{ p.price_minor | money: p.currency }}</span>
            @if (p.compare_at_minor) {
              <s class="was">{{ p.compare_at_minor | money: p.currency }}</s>
            }
          </p>
        </div>
      </div>
    </a>
    <button
      type="button"
      class="add"
      [class.done]="state() === 'added'"
      [disabled]="p.availability === 'OUT_OF_STOCK' || state() === 'adding'"
      [attr.aria-label]="'Add ' + p.name + ' to cart'"
      (click)="addToCart()"
    >
      @switch (p.availability === 'OUT_OF_STOCK' ? 'sold' : state()) {
        @case ('sold') {
          Sold out
        }
        @case ('adding') {
          Adding…
        }
        @case ('added') {
          <shr-icon name="check" /> Added
        }
        @default {
          <shr-icon name="bag" /> Add to cart
        }
      }
    </button>
    @if (error()) {
      <p class="err" role="alert">{{ error() }}</p>
    }
  `,
  styles: `
    :host {
      display: flex;
      flex-direction: column;
      gap: var(--space-3);
      padding: var(--space-3);
      border: 1px solid var(--color-border);
      border-radius: var(--radius-lg);
      background: var(--color-surface);
      transition:
        border-color var(--duration-fast) ease,
        box-shadow var(--duration-base) var(--ease-out),
        translate var(--duration-base) var(--ease-out);
    }
    :host(:hover),
    :host(:focus-within) {
      translate: 0 -4px;
      border-color: color-mix(in srgb, var(--color-primary) 40%, var(--color-border));
      box-shadow: var(--shadow-lg);
    }
    .card-link {
      display: flex;
      flex: 1;
      flex-direction: column;
      color: inherit;
      text-decoration: none;
    }
    .card-link:focus-visible {
      box-shadow: var(--focus-ring);
      border-radius: var(--radius-md);
    }
    .image {
      position: relative;
      aspect-ratio: 1;
      overflow: hidden;
      border-radius: var(--radius-md);
      background: var(--color-surface-alt);
      isolation: isolate;
    }
    img,
    .placeholder {
      width: 100%;
      height: 100%;
      object-fit: cover;
      transition: transform 900ms var(--ease-out);
    }
    .placeholder {
      display: grid;
      place-items: center;
      color: var(--color-muted);
      --icon-size: 40px;
      opacity: 0.6;
    }
    :host(:hover) img,
    .card-link:focus-visible img {
      transform: scale(1.04);
    }
    .badge {
      position: absolute;
      top: var(--space-2);
      left: var(--space-2);
      padding: 2px var(--space-2);
      border-radius: var(--radius-sm);
      font-size: var(--font-size-xs);
      font-weight: 600;
      background: var(--color-surface);
      color: var(--color-text);
      box-shadow: var(--shadow-sm);
    }
    .badge.sale {
      background: var(--color-sale);
      color: var(--color-primary-contrast);
    }
    .badge.sold {
      background: var(--color-text);
      color: var(--color-surface);
    }
    .body {
      display: flex;
      flex: 1;
      flex-direction: column;
      padding: var(--space-3) var(--space-1) 0;
    }
    h3 {
      margin: 0;
      font-size: var(--font-size-md);
      font-weight: var(--font-weight-medium);
      letter-spacing: 0;
      line-height: var(--line-height-heading);
      transition: color var(--duration-fast) ease;
    }
    .card-link:hover h3 {
      color: var(--color-primary);
    }
    .short {
      margin: var(--space-1) 0 0;
      color: var(--color-muted);
      font-size: var(--font-size-sm);
      display: -webkit-box;
      -webkit-line-clamp: 1;
      -webkit-box-orient: vertical;
      overflow: hidden;
    }
    .foot {
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      justify-content: space-between;
      gap: var(--space-2);
      margin-top: auto;
      padding-top: var(--space-3);
    }
    .price {
      display: flex;
      flex-wrap: wrap;
      align-items: baseline;
      gap: 0 var(--space-2);
      margin: 0;
      font-weight: 700;
    }
    .now {
      color: var(--color-sale);
    }
    .was {
      color: var(--color-muted);
      font-weight: 400;
      font-size: var(--font-size-sm);
    }
    .add {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      gap: var(--space-2);
      width: 100%;
      min-height: 40px;
      padding: 0 var(--space-3);
      border: 1px solid var(--color-primary);
      border-radius: var(--radius-md);
      background: var(--color-primary);
      color: var(--color-primary-contrast);
      font: inherit;
      font-size: var(--font-size-sm);
      font-weight: 600;
      cursor: pointer;
      --icon-size: 16px;
      transition:
        background-color var(--duration-fast) ease,
        border-color var(--duration-fast) ease,
        transform var(--duration-fast) var(--ease-out);
    }
    .add:hover:not(:disabled) {
      background: var(--color-primary-hover);
    }
    .add:active:not(:disabled) {
      transform: scale(0.97);
    }
    .add:disabled {
      cursor: not-allowed;
      opacity: 0.55;
    }
    .add.done,
    .add.done:hover:not(:disabled) {
      background: var(--color-success);
      border-color: var(--color-success);
    }
    .add.done shr-icon {
      animation: pop 420ms var(--ease-out);
    }
    .err {
      margin: 0;
      color: var(--color-danger);
      font-size: var(--font-size-xs);
    }
    @media (max-width: 560px) {
      :host {
        padding: var(--space-2);
        gap: var(--space-2);
      }
      .short {
        display: none;
      }
    }
  `,
})
export class ProductCard {
  readonly product = input.required<Card>();
  protected readonly link = computed(() => productLink(this.product()));
  private readonly auth = inject(AuthService);
  private readonly cart = inject(CartStore);
  private readonly router = inject(Router);

  protected readonly state = signal<'idle' | 'adding' | 'added'>('idle');
  protected readonly error = signal<string | null>(null);
  private resetTimer: ReturnType<typeof setTimeout> | undefined;

  /** Adds one of this product straight from the card. Signed-out visitors go to sign in first. */
  protected async addToCart(): Promise<void> {
    if (this.auth.user()?.user_type !== 'BUYER') {
      // ADR 0004: sign-in is required before using the cart.
      await this.router.navigate(['/login'], { queryParams: { returnUrl: this.router.url } });
      return;
    }
    clearTimeout(this.resetTimer);
    this.state.set('adding');
    this.error.set(null);
    try {
      await this.cart.add(this.product().sku_id);
      this.state.set('added');
      this.resetTimer = setTimeout(() => this.state.set('idle'), 2000);
    } catch (err) {
      this.state.set('idle');
      this.error.set(apiErrorMessage(err));
    }
  }

  /**
   * Names this card's picture for the page transition, so it grows into the product page's
   * main picture (which carries the same name). Only the clicked card gets the name.
   */
  protected morph(event: MouseEvent): void {
    if (event.ctrlKey || event.metaKey || event.shiftKey || event.button !== 0) return;
    const img = (event.currentTarget as HTMLElement).querySelector<HTMLElement>('.image img');
    if (img) img.style.viewTransitionName = 'product-image';
  }
  protected readonly discount = computed(() => {
    const p = this.product();
    if (!p.compare_at_minor || p.compare_at_minor <= p.price_minor) return 0;
    return Math.round((1 - p.price_minor / p.compare_at_minor) * 100);
  });
}
