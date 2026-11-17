import { DatePipe } from '@angular/common';
import { Component, computed, inject, signal } from '@angular/core';
import { rxResource } from '@angular/core/rxjs-interop';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { MoneyPipe, RETURN_REASON_LABEL, RETURN_STATUS_LABEL, ReturnStatus } from '@shop/shared';
import { ReturnsApi } from './returns.api';

@Component({
  selector: 'adm-return-list',
  imports: [FormsModule, RouterLink, MoneyPipe, DatePipe],
  template: `
    <div class="page-head">
      <div>
        <h1>Returns</h1>
        <p class="muted">
          Buyers ask from their order page after delivery. Approve or reject, mark the parcel
          received, then record the refund you paid.
        </p>
      </div>
    </div>

    <form class="filters" (ngSubmit)="q.set(search.trim()); page.set(1)">
      <label class="visually-hidden" for="q">Search</label>
      <input
        id="q"
        name="q"
        type="search"
        placeholder="Return or order no., name or phone"
        [(ngModel)]="search"
      />
      <label class="visually-hidden" for="status">Status</label>
      <select
        id="status"
        name="status"
        [ngModel]="statusFilter()"
        (ngModelChange)="statusFilter.set($event); page.set(1)"
      >
        <option value="">All statuses</option>
        @for (s of statuses; track s) {
          <option [value]="s">{{ labels[s] }}</option>
        }
      </select>
      <button class="btn btn-secondary" type="submit">Search</button>
    </form>

    @if (returns.error()) {
      <div class="alert-error" role="alert">
        Couldn't load returns.
        <button class="btn btn-secondary" type="button" (click)="returns.reload()">Retry</button>
      </div>
    } @else {
      <div class="card table-wrap">
        <table>
          <thead>
            <tr>
              <th scope="col">Return no.</th>
              <th scope="col">Asked</th>
              <th scope="col">Order</th>
              <th scope="col">Customer</th>
              <th scope="col">Reason</th>
              <th scope="col" class="num">Items value</th>
              <th scope="col">Status</th>
            </tr>
          </thead>
          <tbody>
            @for (r of returns.value()?.items ?? []; track r.id) {
              <tr>
                <td class="nowrap">
                  <a [routerLink]="['/returns', r.id]">{{ r.return_number }}</a>
                </td>
                <td>{{ r.requested_at | date: 'dd MMM yyyy' }}</td>
                <td class="nowrap">
                  <a [routerLink]="['/orders', r.order_id]">{{ r.order_number }}</a>
                </td>
                <td>
                  {{ r.customer_name }}<br /><small>{{ r.ship_phone }}</small>
                </td>
                <td>{{ reasons[r.reason] }}</td>
                <td class="num">{{ r.items_value_minor | money: r.currency }}</td>
                <td>
                  <span class="chip" [attr.data-status]="r.status">{{ labels[r.status] }}</span>
                </td>
              </tr>
            } @empty {
              <tr>
                <td colspan="7" class="empty">
                  {{ returns.isLoading() ? 'Loading…' : 'No returns found.' }}
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
  styleUrls: ['../products/admin-table.scss', './returns.scss'],
})
export class ReturnList {
  private readonly api = inject(ReturnsApi);

  protected readonly labels = RETURN_STATUS_LABEL;
  protected readonly reasons = RETURN_REASON_LABEL;
  protected readonly statuses = Object.keys(RETURN_STATUS_LABEL) as ReturnStatus[];

  protected search = '';
  protected readonly q = signal('');
  protected readonly statusFilter = signal<ReturnStatus | ''>('');
  protected readonly page = signal(1);

  protected readonly returns = rxResource({
    params: () => ({ q: this.q(), status: this.statusFilter(), page: this.page() }),
    stream: ({ params }) => this.api.list(params.page, params.status, params.q),
  });
  protected readonly pages = computed(() => {
    const v = this.returns.value();
    return v ? Math.max(1, Math.ceil(v.total / v.page_size)) : 1;
  });
}
