import { Component, computed, inject, input } from '@angular/core';
import { rxResource, toSignal } from '@angular/core/rxjs-interop';
import { FormsModule } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { ProductSort } from '@shop/shared';
import { CatalogApi } from './catalog.api';
import { ProductCard } from './product-card';

const PAGE_SIZE = 24;

/** Product listing. All filters live in the URL so results can be shared and bookmarked. */
@Component({
  selector: 'buy-catalog-page',
  imports: [FormsModule, RouterLink, ProductCard],
  template: `
    <div class="layout">
      <aside aria-label="Categories">
        <h2>Categories</h2>
        <ul>
          <li>
            <a
              [routerLink]="[]"
              [queryParams]="{ category: null, page: null }"
              queryParamsHandling="merge"
              [class.active]="!category()"
              >All products</a
            >
          </li>
          @for (c of categories() ?? []; track c.id) {
            <li [class.child]="c.parent_id">
              <a
                [routerLink]="[]"
                [queryParams]="{ category: c.slug, page: null }"
                queryParamsHandling="merge"
                [class.active]="category() === c.slug"
                >{{ c.name }}</a
              >
            </li>
          }
        </ul>
      </aside>

      <section>
        <form class="toolbar" role="search" (ngSubmit)="search(searchBox.value)">
          <label class="visually-hidden" for="q">Search products</label>
          <input
            #searchBox
            id="q"
            type="search"
            placeholder="Search by name or product number"
            [value]="q() ?? ''"
          />
          <button class="btn" type="submit">Search</button>
          <label class="visually-hidden" for="sort">Sort by</label>
          <select
            id="sort"
            [ngModel]="sortKey()"
            name="sort"
            (ngModelChange)="navigate({ sort: $event, page: null })"
          >
            <option value="newest">Newest</option>
            <option value="price_asc">Price: low to high</option>
            <option value="price_desc">Price: high to low</option>
            <option value="name">Name</option>
          </select>
        </form>

        @if (products.isLoading()) {
          <div class="grid" aria-busy="true">
            @for (i of skeletons; track i) {
              <div class="skeleton"></div>
            }
          </div>
        } @else if (products.error()) {
          <div class="alert-error" role="alert">
            We couldn't load products.
            <button class="btn btn-secondary" type="button" (click)="products.reload()">
              Try again
            </button>
          </div>
        } @else if (products.value(); as result) {
          <p class="count" aria-live="polite">
            {{ result.total }} {{ result.total === 1 ? 'product' : 'products' }}
          </p>
          @if (result.items.length === 0) {
            <p class="empty">No products match. Try a different search or category.</p>
          } @else {
            <div class="grid">
              @for (p of result.items; track p.slug) {
                <buy-product-card [product]="p" />
              }
            </div>
            @if (pages() > 1) {
              <nav class="pager" aria-label="Pagination">
                <button
                  class="btn btn-secondary"
                  type="button"
                  [disabled]="pageNumber() <= 1"
                  (click)="navigate({ page: pageNumber() - 1 })"
                >
                  Previous
                </button>
                <span>Page {{ pageNumber() }} of {{ pages() }}</span>
                <button
                  class="btn btn-secondary"
                  type="button"
                  [disabled]="pageNumber() >= pages()"
                  (click)="navigate({ page: pageNumber() + 1 })"
                >
                  Next
                </button>
              </nav>
            }
          }
        }
      </section>
    </div>
  `,
  styles: `
    .layout {
      display: grid;
      grid-template-columns: 220px 1fr;
      gap: var(--space-6);
    }
    aside h2 {
      font-size: var(--font-size-md);
      margin-top: 0;
    }
    aside ul {
      list-style: none;
      padding: 0;
      margin: 0;
    }
    aside li a {
      display: block;
      padding: var(--space-1) var(--space-2);
      border-radius: var(--radius-sm);
      color: var(--color-text);
      text-decoration: none;
    }
    aside li.child a {
      padding-left: var(--space-6);
    }
    aside a.active {
      background: color-mix(in srgb, var(--color-primary) 10%, transparent);
      color: var(--color-primary);
      font-weight: 600;
    }
    .toolbar {
      display: flex;
      gap: var(--space-2);
      margin-bottom: var(--space-4);
      flex-wrap: wrap;
    }
    .toolbar input {
      flex: 1;
      min-width: 180px;
    }
    .toolbar input,
    .toolbar select {
      padding: var(--space-2) var(--space-3);
      border: 1px solid var(--color-border);
      border-radius: var(--radius-md);
      font: inherit;
      background: var(--color-surface);
    }
    .grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
      gap: var(--space-4);
    }
    .skeleton {
      aspect-ratio: 3 / 4;
      border-radius: var(--radius-md);
      background: linear-gradient(
        90deg,
        var(--color-border),
        var(--color-background),
        var(--color-border)
      );
      background-size: 200% 100%;
      animation: shimmer 1.2s infinite;
    }
    @keyframes shimmer {
      to {
        background-position: -200% 0;
      }
    }
    .count,
    .empty {
      color: var(--color-muted);
    }
    .pager {
      display: flex;
      justify-content: center;
      align-items: center;
      gap: var(--space-4);
      margin-top: var(--space-6);
    }
    @media (max-width: 768px) {
      .layout {
        grid-template-columns: 1fr;
      }
      aside ul {
        display: flex;
        flex-wrap: wrap;
        gap: var(--space-2);
      }
      aside li.child a {
        padding-left: var(--space-2);
      }
    }
  `,
})
export class CatalogPage {
  private readonly api = inject(CatalogApi);
  private readonly router = inject(Router);

  // Bound from query parameters (withComponentInputBinding).
  readonly q = input<string>();
  readonly category = input<string>();
  readonly sort = input<string>();
  readonly page = input<string>();

  protected readonly sortKey = computed<ProductSort>(() => {
    const s = this.sort();
    return s === 'price_asc' || s === 'price_desc' || s === 'name' ? s : 'newest';
  });
  protected readonly pageNumber = computed(() => Math.max(1, Number(this.page()) || 1));
  protected readonly skeletons = Array.from({ length: 8 }, (_, i) => i);

  protected readonly categories = toSignal(this.api.categories());
  protected readonly products = rxResource({
    params: () => ({
      q: this.q(),
      category: this.category(),
      sort: this.sortKey(),
      page: this.pageNumber(),
    }),
    stream: ({ params }) => this.api.products({ ...params, pageSize: PAGE_SIZE }),
  });
  protected readonly pages = computed(() =>
    Math.ceil((this.products.value()?.total ?? 0) / PAGE_SIZE),
  );

  protected search(term: string): void {
    this.navigate({ q: term.trim() || null, page: null });
  }

  protected navigate(params: Record<string, string | number | null>): void {
    void this.router.navigate([], { queryParams: params, queryParamsHandling: 'merge' });
  }
}
