import { Component, computed, inject, input, linkedSignal } from '@angular/core';
import { rxResource } from '@angular/core/rxjs-interop';
import { HttpErrorResponse } from '@angular/common/http';
import { Title } from '@angular/platform-browser';
import { RouterLink } from '@angular/router';
import { AVAILABILITY_LABEL, MoneyPipe } from '@shop/shared';
import { tap } from 'rxjs';
import { CatalogApi } from './catalog.api';

@Component({
  selector: 'buy-product-page',
  imports: [RouterLink, MoneyPipe],
  template: `
    @if (product.isLoading()) {
      <p aria-busy="true">Loading…</p>
    } @else if (notFound()) {
      <h1>Product not found</h1>
      <p>It may have been removed. <a routerLink="/">Browse the catalogue</a></p>
    } @else if (product.error()) {
      <div class="alert-error" role="alert">
        We couldn't load this product.
        <button class="btn btn-secondary" type="button" (click)="product.reload()">
          Try again
        </button>
      </div>
    } @else if (product.value(); as p) {
      <nav class="crumbs" aria-label="Breadcrumb">
        <a routerLink="/">Shop</a> /
        <a routerLink="/" [queryParams]="{ category: p.category.slug }">{{ p.category.name }}</a>
      </nav>
      <div class="layout">
        <div class="gallery">
          <div class="main-image">
            @if (selected(); as m) {
              <img [src]="m.url" [alt]="m.alt_text || p.name" />
            } @else {
              <div class="placeholder">No image</div>
            }
          </div>
          @if (p.media.length > 1) {
            <div class="thumbs" role="list">
              @for (m of p.media; track m.id) {
                <button
                  type="button"
                  role="listitem"
                  [class.active]="m.id === selected()?.id"
                  (click)="selected.set(m)"
                  [attr.aria-label]="'Show image ' + ($index + 1)"
                >
                  <img [src]="m.url" alt="" loading="lazy" />
                </button>
              }
            </div>
          }
        </div>

        <div class="info">
          <h1>{{ p.name }}</h1>
          <p class="number">Product no. {{ p.product_number }}</p>
          <p class="price">
            {{ p.price_minor | money: p.currency }}
            @if (p.compare_at_minor) {
              <s>{{ p.compare_at_minor | money: p.currency }}</s>
            }
          </p>
          <p class="stock" [class.out]="p.availability === 'OUT_OF_STOCK'">
            {{ labels[p.availability] }}
          </p>
          <p>{{ p.short_description }}</p>
          <button class="btn buy" type="button" [disabled]="p.availability === 'OUT_OF_STOCK'">
            {{ p.availability === 'OUT_OF_STOCK' ? 'Out of stock' : 'Add to cart' }}
          </button>
          <p class="note">Cart and checkout are coming in the next update.</p>

          @if (p.description) {
            <h2>Description</h2>
            <p class="description">{{ p.description }}</p>
          }
          @if (p.attributes.length) {
            <h2>Specifications</h2>
            <dl>
              @for (a of p.attributes; track a.name) {
                <dt>{{ a.name }}</dt>
                <dd>{{ a.value }}</dd>
              }
            </dl>
          }
        </div>
      </div>
    }
  `,
  styles: `
    .crumbs {
      font-size: var(--font-size-sm);
      color: var(--color-muted);
      margin-bottom: var(--space-4);
    }
    .layout {
      display: grid;
      grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
      gap: var(--space-8);
    }
    .main-image {
      aspect-ratio: 1;
      background: var(--color-surface);
      border: 1px solid var(--color-border);
      border-radius: var(--radius-md);
      overflow: hidden;
    }
    .main-image img,
    .placeholder {
      width: 100%;
      height: 100%;
      object-fit: contain;
      display: grid;
      place-items: center;
      color: var(--color-muted);
    }
    .thumbs {
      display: flex;
      gap: var(--space-2);
      margin-top: var(--space-2);
      overflow-x: auto;
    }
    .thumbs button {
      width: 64px;
      height: 64px;
      padding: 0;
      border: 2px solid var(--color-border);
      border-radius: var(--radius-sm);
      background: none;
      cursor: pointer;
      overflow: hidden;
    }
    .thumbs button.active {
      border-color: var(--color-primary);
    }
    .thumbs img {
      width: 100%;
      height: 100%;
      object-fit: cover;
    }
    h1 {
      font-size: var(--font-size-xl);
      margin: 0;
    }
    .number {
      color: var(--color-muted);
      margin: 0;
    }
    .price {
      font-size: var(--font-size-lg);
      font-weight: 700;
    }
    .price s {
      color: var(--color-muted);
      font-weight: 400;
      font-size: var(--font-size-md);
    }
    .stock {
      color: var(--color-success);
      font-weight: 600;
    }
    .stock.out {
      color: var(--color-danger);
    }
    .buy {
      min-width: 200px;
    }
    .note {
      color: var(--color-muted);
      font-size: var(--font-size-sm);
    }
    .description {
      white-space: pre-line;
    }
    dl {
      display: grid;
      grid-template-columns: max-content 1fr;
      gap: var(--space-2) var(--space-6);
    }
    dt {
      font-weight: 600;
    }
    dd {
      margin: 0;
    }
    @media (max-width: 768px) {
      .layout {
        grid-template-columns: 1fr;
        gap: var(--space-4);
      }
    }
  `,
})
export class ProductPage {
  private readonly api = inject(CatalogApi);
  private readonly title = inject(Title);

  readonly slug = input.required<string>();
  protected readonly labels = AVAILABILITY_LABEL;

  protected readonly product = rxResource({
    params: () => this.slug(),
    stream: ({ params }) => this.api.product(params).pipe(tap((p) => this.title.setTitle(p.name))),
  });
  protected readonly notFound = computed(() => {
    const err = this.product.error();
    return err instanceof HttpErrorResponse && err.status === 404;
  });
  protected readonly selected = linkedSignal(() => {
    const media = this.product.value()?.media ?? [];
    return media.find((m) => m.is_primary) ?? media[0] ?? null;
  });
}
