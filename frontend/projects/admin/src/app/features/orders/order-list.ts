import { DatePipe } from '@angular/common';
import { Component, computed, inject, signal } from '@angular/core';
import { rxResource } from '@angular/core/rxjs-interop';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { MoneyPipe, ORDER_STATUS_LABEL, OrderStatus, OrderStatusBadge } from '@shop/shared';
import { AdminOrdersApi } from './admin-orders.api';

@Component({
  selector: 'adm-order-list',
  imports: [FormsModule, RouterLink, MoneyPipe, DatePipe, OrderStatusBadge],
  template: `
    <div class="page-head">
      <h1>Orders</h1>
    </div>

    <form class="filters" (ngSubmit)="apply()">
      <label class="visually-hidden" for="q">Search</label>
      <input
        id="q"
        name="q"
        type="search"
        placeholder="Order no., name, phone or email"
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
        @for (s of statuses; track s) {
          <option [value]="s">{{ labels[s] }}</option>
        }
      </select>
      <label for="from">From</label>
      <input
        id="from"
        name="from"
        type="date"
        [ngModel]="dateFrom()"
        (ngModelChange)="dateFrom.set($event); page.set(1)"
      />
      <label for="to">To</label>
      <input
        id="to"
        name="to"
        type="date"
        [ngModel]="dateTo()"
        (ngModelChange)="dateTo.set($event); page.set(1)"
      />
      <button class="btn btn-secondary" type="submit">Search</button>
    </form>

    @if (orders.error()) {
      <div class="alert-error" role="alert">
        Couldn't load orders.
        <button class="btn btn-secondary" type="button" (click)="orders.reload()">Retry</button>
      </div>
    } @else {
      <div class="card table-wrap">
        <table>
          <thead>
            <tr>
              <th scope="col">Order no.</th>
              <th scope="col">Placed</th>
              <th scope="col">Customer</th>
              <th scope="col">City</th>
              <th scope="col" class="num">Items</th>
              <th scope="col" class="num">Total</th>
              <th scope="col">Payment</th>
              <th scope="col">Status</th>
            </tr>
          </thead>
          <tbody>
            @for (o of orders.value()?.items ?? []; track o.id) {
              <tr>
                <td class="nowrap">
                  <a [routerLink]="['/orders', o.id]">{{ o.order_number }}</a>
                </td>
                <td>{{ o.placed_at | date: 'dd MMM yyyy, HH:mm' }}</td>
                <td>
                  {{ o.customer_name }}<br /><small>{{ o.ship_phone }}</small>
                </td>
                <td>{{ o.ship_city }}</td>
                <td class="num">{{ o.item_count }}</td>
                <td class="num">{{ o.total_minor | money: o.currency }}</td>
                <td>{{ o.payment_method }} · {{ o.payment_status.toLowerCase() }}</td>
                <td><shr-order-status [status]="o.status" /></td>
              </tr>
            } @empty {
              <tr>
                <td colspan="8" class="empty">
                  {{ orders.isLoading() ? 'Loading…' : 'No orders found.' }}
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
  styleUrl: '../products/admin-table.scss',
})
export class OrderList {
  private readonly api = inject(AdminOrdersApi);

  protected readonly labels = ORDER_STATUS_LABEL;
  protected readonly statuses = Object.keys(ORDER_STATUS_LABEL) as OrderStatus[];

  protected search = '';
  protected readonly q = signal('');
  protected readonly status = signal<OrderStatus | ''>('');
  protected readonly dateFrom = signal('');
  protected readonly dateTo = signal('');
  protected readonly page = signal(1);

  protected readonly orders = rxResource({
    params: () => ({
      q: this.q(),
      status: this.status(),
      dateFrom: this.dateFrom(),
      dateTo: this.dateTo(),
      page: this.page(),
    }),
    stream: ({ params }) => this.api.orders(params),
  });
  protected readonly pages = computed(() => Math.ceil((this.orders.value()?.total ?? 0) / 20));

  protected apply(): void {
    this.q.set(this.search.trim());
    this.page.set(1);
  }
}
