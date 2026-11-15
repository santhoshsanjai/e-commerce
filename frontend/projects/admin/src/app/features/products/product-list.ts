import { Component, computed, inject, signal } from '@angular/core';
import { rxResource } from '@angular/core/rxjs-interop';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { HasPermissionDirective, MoneyPipe, ProductStatus } from '@shop/shared';
import { AdminCatalogApi } from './admin-catalog.api';
import { StatusChip } from './status-chip';

@Component({
  selector: 'adm-product-list',
  imports: [FormsModule, RouterLink, MoneyPipe, StatusChip, HasPermissionDirective],
  template: `
    <div class="page-head">
      <h1>Products</h1>
      <a *shrHasPermission="'products.create'" class="btn" routerLink="/products/new"
        >New product</a
      >
    </div>

    <form class="filters" (ngSubmit)="q.set(search); page.set(1)">
      <label class="visually-hidden" for="q">Search</label>
      <input
        id="q"
        name="q"
        type="search"
        placeholder="Name or product number"
        [(ngModel)]="search"
      />
      <label class="visually-hidden" for="status">Status</label>
      <select
        id="status"
        name="status"
        [ngModel]="status()"
        (ngModelChange)="status.set($event); page.set(1)"
      >
        <option value="">All statuses</option>
        <option value="DRAFT">Draft</option>
        <option value="PUBLISHED">Published</option>
        <option value="ARCHIVED">Archived</option>
      </select>
      <button class="btn btn-secondary" type="submit">Search</button>
    </form>

    @if (products.error()) {
      <div class="alert-error" role="alert">
        Couldn't load products.
        <button class="btn btn-secondary" type="button" (click)="products.reload()">Retry</button>
      </div>
    } @else {
      <div class="card table-wrap">
        <table>
          <thead>
            <tr>
              <th scope="col"><span class="visually-hidden">Image</span></th>
              <th scope="col">Product no.</th>
              <th scope="col">Name</th>
              <th scope="col">Category</th>
              <th scope="col" class="num">Price</th>
              <th scope="col" class="num">Stock</th>
              <th scope="col">Status</th>
            </tr>
          </thead>
          <tbody>
            @for (p of products.value()?.items ?? []; track p.id) {
              <tr>
                <td>
                  @if (p.primary_image_url) {
                    <img [src]="p.primary_image_url" alt="" width="40" height="40" />
                  }
                </td>
                <td>
                  <a [routerLink]="['/products', p.id]">{{ p.product_number }}</a>
                </td>
                <td>{{ p.name }}</td>
                <td>{{ p.category_name }}</td>
                <td class="num">{{ p.price_minor | money: p.currency }}</td>
                <td class="num">{{ p.stock_qty }}</td>
                <td><adm-status-chip [status]="p.status" /></td>
              </tr>
            } @empty {
              <tr>
                <td colspan="7" class="empty">
                  {{ products.isLoading() ? 'Loading…' : 'No products found.' }}
                </td>
              </tr>
            }
          </tbody>
        </table>
      </div>
      @if (pages() > 1) {
        <nav class="pager" aria-label="Pagination">
          <button
            class="btn btn-secondary"
            type="button"
            [disabled]="page() <= 1"
            (click)="page.set(page() - 1)"
          >
            Previous
          </button>
          <span>Page {{ page() }} of {{ pages() }}</span>
          <button
            class="btn btn-secondary"
            type="button"
            [disabled]="page() >= pages()"
            (click)="page.set(page() + 1)"
          >
            Next
          </button>
        </nav>
      }
    }
  `,
  styleUrl: './admin-table.scss',
})
export class ProductList {
  private readonly api = inject(AdminCatalogApi);

  protected search = '';
  protected readonly q = signal('');
  protected readonly status = signal<ProductStatus | ''>('');
  protected readonly page = signal(1);

  protected readonly products = rxResource({
    params: () => ({ q: this.q(), status: this.status(), page: this.page() }),
    stream: ({ params }) => this.api.products(params),
  });
  protected readonly pages = computed(() => Math.ceil((this.products.value()?.total ?? 0) / 20));
}
