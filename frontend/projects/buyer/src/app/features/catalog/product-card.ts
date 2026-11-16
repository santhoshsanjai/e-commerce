import { Component, computed, input } from '@angular/core';
import { RouterLink } from '@angular/router';
import { Icon, MoneyPipe, ProductCard as Card } from '@shop/shared';

@Component({
  selector: 'buy-product-card',
  imports: [RouterLink, MoneyPipe, Icon],
  template: `
    @let p = product();
    <a class="card-link" [routerLink]="['/products', p.slug]">
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
        <span class="quick" aria-hidden="true">View details <shr-icon name="arrow" /></span>
      </div>
      <div class="body">
        <h3>{{ p.name }}</h3>
        @if (p.short_description) {
          <p class="short">{{ p.short_description }}</p>
        }
        <p class="price">
          <span [class.now]="p.compare_at_minor">{{ p.price_minor | money: p.currency }}</span>
          @if (p.compare_at_minor) {
            <s class="was">{{ p.compare_at_minor | money: p.currency }}</s>
          }
        </p>
      </div>
    </a>
  `,
  styles: `
    :host {
      display: block;
    }
    .card-link {
      display: flex;
      flex-direction: column;
      height: 100%;
      color: inherit;
      text-decoration: none;
    }
    .image {
      position: relative;
      aspect-ratio: 4 / 5;
      overflow: hidden;
      border-radius: var(--radius-lg);
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
    .card-link:hover img,
    .card-link:focus-visible img {
      transform: scale(1.06);
    }
    .badge {
      position: absolute;
      top: var(--space-3);
      left: var(--space-3);
      padding: 4px var(--space-3);
      border-radius: var(--radius-pill);
      font-size: var(--font-size-xs);
      font-weight: 600;
      letter-spacing: 0.04em;
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
    .quick {
      position: absolute;
      left: var(--space-3);
      right: var(--space-3);
      bottom: var(--space-3);
      display: flex;
      align-items: center;
      justify-content: center;
      gap: var(--space-2);
      min-height: 42px;
      border-radius: var(--radius-pill);
      background: color-mix(in srgb, var(--color-surface) 92%, transparent);
      backdrop-filter: blur(8px);
      color: var(--color-text);
      font-size: var(--font-size-sm);
      font-weight: 600;
      opacity: 0;
      transform: translateY(12px);
      transition:
        opacity var(--duration-base) var(--ease-out),
        transform var(--duration-base) var(--ease-out);
      --icon-size: 16px;
    }
    .card-link:hover .quick,
    .card-link:focus-visible .quick {
      opacity: 1;
      transform: none;
    }
    .body {
      padding: var(--space-4) var(--space-1) 0;
    }
    h3 {
      margin: 0;
      font-size: var(--font-size-md);
      font-weight: 500;
      line-height: 1.35;
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
    .price {
      display: flex;
      align-items: baseline;
      gap: var(--space-2);
      margin: var(--space-2) 0 0;
      font-weight: 600;
    }
    .now {
      color: var(--color-sale);
    }
    .was {
      color: var(--color-muted);
      font-weight: 400;
      font-size: var(--font-size-sm);
    }
    @media (hover: none) {
      .quick {
        display: none;
      }
    }
  `,
})
export class ProductCard {
  readonly product = input.required<Card>();
  protected readonly discount = computed(() => {
    const p = this.product();
    if (!p.compare_at_minor || p.compare_at_minor <= p.price_minor) return 0;
    return Math.round((1 - p.price_minor / p.compare_at_minor) * 100);
  });
}
