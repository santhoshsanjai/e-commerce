import { Component, input } from '@angular/core';
import { RouterLink } from '@angular/router';
import { AVAILABILITY_LABEL, MoneyPipe, ProductCard as Card } from '@shop/shared';

@Component({
  selector: 'buy-product-card',
  imports: [RouterLink, MoneyPipe],
  template: `
    @let p = product();
    <a class="card-link" [routerLink]="['/products', p.slug]">
      <div class="image">
        @if (p.image_url) {
          <img [src]="p.image_url" [alt]="p.image_alt" loading="lazy" />
        } @else {
          <div class="placeholder" aria-hidden="true">No image</div>
        }
      </div>
      <div class="body">
        <h3>{{ p.name }}</h3>
        <p class="number">{{ p.product_number }}</p>
        <p class="price">
          {{ p.price_minor | money: p.currency }}
          @if (p.compare_at_minor) {
            <s class="was">{{ p.compare_at_minor | money: p.currency }}</s>
          }
        </p>
        <p class="stock" [class.out]="p.availability === 'OUT_OF_STOCK'">
          {{ labels[p.availability] }}
        </p>
      </div>
    </a>
  `,
  styles: `
    .card-link {
      display: flex;
      flex-direction: column;
      height: 100%;
      background: var(--color-surface);
      border: 1px solid var(--color-border);
      border-radius: var(--radius-md);
      overflow: hidden;
      color: inherit;
      text-decoration: none;
      transition: box-shadow 0.15s;
    }
    .card-link:hover {
      box-shadow: var(--shadow-sm);
    }
    .image {
      aspect-ratio: 1;
      background: var(--color-background);
    }
    img,
    .placeholder {
      width: 100%;
      height: 100%;
      object-fit: cover;
      display: grid;
      place-items: center;
      color: var(--color-muted);
    }
    .body {
      padding: var(--space-3);
    }
    h3 {
      font-size: var(--font-size-md);
      margin: 0;
    }
    .number {
      margin: 0;
      color: var(--color-muted);
      font-size: var(--font-size-sm);
    }
    .price {
      margin: var(--space-2) 0 0;
      font-weight: 700;
    }
    .was {
      color: var(--color-muted);
      font-weight: 400;
      margin-left: var(--space-2);
    }
    .stock {
      margin: 0;
      font-size: var(--font-size-sm);
      color: var(--color-success);
    }
    .stock.out {
      color: var(--color-danger);
    }
  `,
})
export class ProductCard {
  readonly product = input.required<Card>();
  protected readonly labels = AVAILABILITY_LABEL;
}
