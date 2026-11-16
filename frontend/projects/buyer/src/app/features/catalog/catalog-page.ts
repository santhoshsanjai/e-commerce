import { Component, computed, inject, input, signal } from '@angular/core';
import { rxResource, toSignal } from '@angular/core/rxjs-interop';
import { FormsModule } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { Icon, ProductSort, RevealDirective } from '@shop/shared';
import { CatalogApi } from './catalog.api';
import { ProductCard } from './product-card';

const PAGE_SIZE = 24;

/** Product listing. All filters live in the URL so results can be shared and bookmarked. */
@Component({
  selector: 'buy-catalog-page',
  imports: [FormsModule, RouterLink, ProductCard, Icon, RevealDirective],
  template: `
    <div class="page-head">
      <nav class="crumbs" aria-label="Breadcrumb">
        <a routerLink="/">Home</a>
        <shr-icon name="chevron-right" />
        <span>Shop</span>
      </nav>
      <h1>{{ heading() }}</h1>
      @if (q()) {
        <p>Showing results for “{{ q() }}”</p>
      }
    </div>

    <div class="layout">
      <aside aria-label="Categories" [class.open]="filtersOpen()">
        <h2>Categories</h2>
        <ul>
          <li>
            <a
              [routerLink]="[]"
              [queryParams]="{ category: null, page: null }"
              queryParamsHandling="merge"
              [class.active]="!category()"
              (click)="filtersOpen.set(false)"
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
                (click)="filtersOpen.set(false)"
                >{{ c.name }}</a
              >
            </li>
          }
        </ul>
      </aside>

      <section class="results">
        <div class="toolbar">
          <button
            type="button"
            class="btn btn-secondary filter-btn"
            [attr.aria-expanded]="filtersOpen()"
            (click)="filtersOpen.set(!filtersOpen())"
          >
            <shr-icon name="sliders" /> Categories
          </button>
          <p class="result-count" aria-live="polite">
            @if (products.value(); as result) {
              {{ result.total }} {{ result.total === 1 ? 'product' : 'products' }}
            }
          </p>
          <label class="sort">
            <span>Sort by</span>
            <select
              id="sort"
              class="select"
              [ngModel]="sortKey()"
              name="sort"
              (ngModelChange)="navigate({ sort: $event, page: null })"
            >
              <option value="newest">Newest</option>
              <option value="price_asc">Price: low to high</option>
              <option value="price_desc">Price: high to low</option>
              <option value="name">Name</option>
            </select>
          </label>
        </div>

        @if (products.isLoading()) {
          <div class="product-grid" aria-busy="true">
            @for (i of skeletons; track i) {
              <div class="sk-card">
                <div class="skeleton sk-image"></div>
                <div class="skeleton skeleton-text sk-w70"></div>
                <div class="skeleton skeleton-text sk-w40"></div>
              </div>
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
          @if (result.items.length === 0) {
            <div class="empty">
              <shr-icon name="search" />
              <h2>No products match</h2>
              <p>Try a different search or browse another category.</p>
              <a class="btn" routerLink="/shop">View all products</a>
            </div>
          } @else {
            <div class="product-grid">
              @for (p of result.items; track p.slug) {
                <buy-product-card [product]="p" [shrReveal]="($index % 4) * 70" />
              }
            </div>
            @if (pages() > 1) {
              <nav class="pager" aria-label="Pagination">
                <button
                  class="page-btn"
                  type="button"
                  aria-label="Previous page"
                  [disabled]="pageNumber() <= 1"
                  (click)="navigate({ page: pageNumber() - 1 })"
                >
                  <shr-icon name="chevron-left" />
                </button>
                @for (n of pageList(); track $index) {
                  @if (n === 0) {
                    <span class="gap" aria-hidden="true">…</span>
                  } @else {
                    <button
                      class="page-btn"
                      type="button"
                      [class.current]="n === pageNumber()"
                      [attr.aria-current]="n === pageNumber() ? 'page' : null"
                      (click)="navigate({ page: n })"
                    >
                      {{ n }}
                    </button>
                  }
                }
                <button
                  class="page-btn"
                  type="button"
                  aria-label="Next page"
                  [disabled]="pageNumber() >= pages()"
                  (click)="navigate({ page: pageNumber() + 1 })"
                >
                  <shr-icon name="chevron-right" />
                </button>
              </nav>
            }
          }
        }
      </section>
    </div>
  `,
  styles: `
    .crumbs {
      display: flex;
      align-items: center;
      gap: var(--space-2);
      font-size: var(--font-size-sm);
      color: var(--color-muted);
      --icon-size: 14px;
      a {
        color: inherit;
        text-decoration: none;
      }
      a:hover {
        color: var(--color-text);
      }
    }
    .layout {
      display: grid;
      grid-template-columns: 220px minmax(0, 1fr);
      gap: var(--space-10);
      align-items: start;
    }
    aside {
      position: sticky;
      top: 150px;
    }
    aside h2 {
      margin: 0 0 var(--space-3);
      font-size: var(--font-size-xs);
      font-weight: 600;
      letter-spacing: var(--tracking-wide);
      text-transform: uppercase;
      color: var(--color-muted);
    }
    aside ul {
      list-style: none;
      padding: 0;
      margin: 0;
    }
    aside li a {
      display: block;
      padding: var(--space-2) var(--space-3);
      border-radius: var(--radius-md);
      color: var(--color-text);
      text-decoration: none;
      transition:
        background-color var(--duration-fast) ease,
        padding var(--duration-base) var(--ease-out);
    }
    aside li a:hover {
      background: var(--color-surface-alt);
      padding-left: var(--space-4);
    }
    aside li.child a {
      padding-left: var(--space-6);
      font-size: var(--font-size-sm);
    }
    aside a.active {
      background: var(--color-primary-soft);
      color: var(--color-primary);
      font-weight: 600;
    }
    .toolbar {
      display: flex;
      align-items: center;
      gap: var(--space-3);
      margin-bottom: var(--space-6);
      padding-bottom: var(--space-4);
      border-bottom: 1px solid var(--color-border);
    }
    .filter-btn {
      display: none;
      --icon-size: 16px;
    }
    .result-count {
      flex: 1;
      margin: 0;
      color: var(--color-muted);
      font-size: var(--font-size-sm);
    }
    .sort {
      display: flex;
      align-items: center;
      gap: var(--space-2);
      font-size: var(--font-size-sm);
      color: var(--color-muted);
    }
    .empty {
      display: grid;
      justify-items: center;
      gap: var(--space-2);
      padding: var(--space-16) var(--space-4);
      text-align: center;
      border: 1px dashed var(--color-border);
      border-radius: var(--radius-lg);
      --icon-size: 36px;
      color: var(--color-muted);
      h2 {
        margin: var(--space-2) 0 0;
        font-family: var(--font-display);
        font-size: var(--font-size-xl);
        color: var(--color-text);
      }
      p {
        margin: 0 0 var(--space-4);
      }
    }
    .pager {
      display: flex;
      justify-content: center;
      align-items: center;
      gap: var(--space-2);
      margin-top: var(--space-12);
    }
    .page-btn {
      display: inline-grid;
      place-items: center;
      min-width: 42px;
      height: 42px;
      padding: 0 var(--space-2);
      border: 1px solid var(--color-border);
      border-radius: var(--radius-pill);
      background: var(--color-surface);
      color: var(--color-text);
      font: inherit;
      cursor: pointer;
      --icon-size: 16px;
      transition: border-color var(--duration-fast) ease;
    }
    .page-btn:hover:not(:disabled) {
      border-color: var(--color-text);
    }
    .page-btn.current {
      background: var(--color-primary);
      border-color: var(--color-primary);
      color: var(--color-primary-contrast);
    }
    .page-btn:disabled {
      opacity: 0.4;
      cursor: not-allowed;
    }
    .gap {
      color: var(--color-muted);
    }
    @media (max-width: 860px) {
      .layout {
        grid-template-columns: minmax(0, 1fr);
        gap: 0;
      }
      aside {
        position: static;
        display: none;
        margin-bottom: var(--space-4);
        animation: fade-up var(--duration-base) var(--ease-out) both;
      }
      aside.open {
        display: block;
      }
      aside ul {
        display: flex;
        flex-wrap: wrap;
        gap: var(--space-2);
      }
      aside li a,
      aside li.child a {
        padding: var(--space-2) var(--space-4);
        border: 1px solid var(--color-border);
        border-radius: var(--radius-pill);
        font-size: var(--font-size-sm);
      }
      aside li a:hover {
        padding-left: var(--space-4);
      }
      .filter-btn {
        display: inline-flex;
        min-height: 40px;
        padding-inline: var(--space-4);
      }
      .sort span {
        display: none;
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
  protected readonly filtersOpen = signal(false);

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

  protected readonly heading = computed(() => {
    const slug = this.category();
    if (slug) return this.categories()?.find((c) => c.slug === slug)?.name ?? 'Shop';
    if (this.q()) return 'Search results';
    return this.sortKey() === 'newest' && this.sort() ? 'New arrivals' : 'All products';
  });

  /** Page numbers to show, with 0 standing for a gap: 1 … 4 5 6 … 12. */
  protected readonly pageList = computed(() => {
    const total = this.pages();
    const current = this.pageNumber();
    const shown = [...new Set([1, current - 1, current, current + 1, total])]
      .filter((n) => n >= 1 && n <= total)
      .sort((a, b) => a - b);
    const list: number[] = [];
    shown.forEach((n, i) => {
      if (i && n - shown[i - 1] > 1) list.push(0);
      list.push(n);
    });
    return list;
  });

  protected navigate(params: Record<string, string | number | null>): void {
    void this.router.navigate([], { queryParams: params, queryParamsHandling: 'merge' });
  }
}
