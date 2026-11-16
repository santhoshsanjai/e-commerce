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
          <span class="details" aria-hidden="true">View details</span>
        </div>
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
      padding: var(--space-3);
      border: 1px solid var(--color-border);
      border-radius: var(--radius-lg);
      background: var(--color-surface);
      color: inherit;
      text-decoration: none;
      transition:
        border-color var(--duration-fast) ease,
        box-shadow var(--duration-base) var(--ease-out);
    }
    .card-link:hover,
    .card-link:focus-visible {
      border-color: color-mix(in srgb, var(--color-primary) 40%, var(--color-border));
      box-shadow: var(--shadow-md);
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
    .card-link:hover img,
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
    .details {
      padding: 6px var(--space-3);
      border-radius: var(--radius-md);
      background: var(--color-primary);
      color: var(--color-primary-contrast);
      font-size: var(--font-size-xs);
      font-weight: 600;
      white-space: nowrap;
    }
    .now {
      color: var(--color-sale);
    }
    .was {
      color: var(--color-muted);
      font-weight: 400;
      font-size: var(--font-size-sm);
    }
    @media (max-width: 560px) {
      .card-link {
        padding: var(--space-2);
      }
      .short,
      .details {
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
