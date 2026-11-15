import { DatePipe } from '@angular/common';
import { Component, computed, inject, signal } from '@angular/core';
import { rxResource } from '@angular/core/rxjs-interop';
import { RouterLink } from '@angular/router';
import { MoneyPipe, OrderStatusBadge } from '@shop/shared';
import { OrdersApi } from './orders.api';

@Component({
  selector: 'buy-order-list-page',
  imports: [RouterLink, MoneyPipe, DatePipe, OrderStatusBadge],
  template: `
    <h1>My orders</h1>
    @if (orders.error()) {
      <div class="alert-error" role="alert">
        We couldn't load your orders.
        <button class="btn btn-secondary" type="button" (click)="orders.reload()">Try again</button>
      </div>
    } @else if (orders.value(); as result) {
      @if (result.items.length === 0) {
        <div class="card">
          <p>You haven't placed any orders yet.</p>
          <a class="btn" routerLink="/">Start shopping</a>
        </div>
      } @else {
        <ul class="order-list">
          @for (o of result.items; track o.order_number) {
            <li>
              <a class="card order-row" [routerLink]="['/orders', o.order_number]">
                <span class="main">
                  <strong>{{ o.order_number }}</strong>
                  <span class="muted">
                    {{ o.placed_at | date: 'mediumDate' }} · {{ o.item_count }}
                    {{ o.item_count === 1 ? 'item' : 'items' }}
                  </span>
                </span>
                <shr-order-status [status]="o.status" />
                <strong class="amount">{{ o.total_minor | money: o.currency }}</strong>
              </a>
            </li>
          }
        </ul>
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
    } @else {
      <p aria-busy="true">Loading…</p>
    }
  `,
  styleUrl: './orders.scss',
})
export class OrderListPage {
  private readonly api = inject(OrdersApi);
  protected readonly page = signal(1);
  protected readonly orders = rxResource({
    params: () => this.page(),
    stream: ({ params }) => this.api.myOrders(params),
  });
  protected readonly pages = computed(() => {
    const v = this.orders.value();
    return v ? Math.ceil(v.total / v.page_size) : 0;
  });
}
