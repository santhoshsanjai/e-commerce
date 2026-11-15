import { DatePipe } from '@angular/common';
import { HttpErrorResponse } from '@angular/common/http';
import { Component, computed, inject, input } from '@angular/core';
import { rxResource } from '@angular/core/rxjs-interop';
import { RouterLink } from '@angular/router';
import { MoneyPipe, ORDER_STATUS_LABEL, OrderStatusBadge } from '@shop/shared';
import { AdminOrdersApi } from './admin-orders.api';

@Component({
  selector: 'adm-order-detail',
  imports: [RouterLink, MoneyPipe, DatePipe, OrderStatusBadge],
  template: `
    <a routerLink="/orders" class="back">← Orders</a>
    @if (order.isLoading()) {
      <p aria-busy="true">Loading…</p>
    } @else if (notFound()) {
      <h1>Order not found</h1>
    } @else if (order.error()) {
      <div class="alert-error" role="alert">
        Couldn't load this order.
        <button class="btn btn-secondary" type="button" (click)="order.reload()">Retry</button>
      </div>
    } @else if (order.value(); as o) {
      <div class="head">
        <h1>{{ o.order_number }}</h1>
        <shr-order-status [status]="o.status" />
      </div>
      <p class="muted">
        Placed {{ o.placed_at | date: 'dd MMM yyyy, HH:mm' }} · {{ o.payment_method }} ({{
          o.payment_status.toLowerCase()
        }})
      </p>

      <div class="grid">
        <section class="card">
          <h2>Items</h2>
          <table>
            <thead>
              <tr>
                <th scope="col">Product</th>
                <th scope="col">SKU</th>
                <th scope="col" class="num">Unit price</th>
                <th scope="col" class="num">Qty</th>
                <th scope="col" class="num">Total</th>
              </tr>
            </thead>
            <tbody>
              @for (item of o.items; track item.sku) {
                <tr>
                  <td>
                    {{ item.product_name }}<br /><small class="muted">{{
                      item.product_number
                    }}</small>
                  </td>
                  <td>{{ item.sku }}</td>
                  <td class="num">{{ item.unit_price_minor | money: o.currency }}</td>
                  <td class="num">{{ item.qty }}</td>
                  <td class="num">{{ item.line_total_minor | money: o.currency }}</td>
                </tr>
              }
            </tbody>
          </table>
          <dl class="totals">
            <dt>Subtotal</dt>
            <dd>{{ o.subtotal_minor | money: o.currency }}</dd>
            <dt>Shipping</dt>
            <dd>{{ o.shipping_minor | money: o.currency }}</dd>
            <dt>Discount</dt>
            <dd>{{ o.discount_minor | money: o.currency }}</dd>
            <dt class="grand">Total (COD to collect)</dt>
            <dd class="grand">{{ o.total_minor | money: o.currency }}</dd>
          </dl>
        </section>

        <div class="side">
          <section class="card">
            <h2>Customer</h2>
            <p>
              {{ o.customer_name }}<br /><span class="muted">{{ o.customer_email }}</span>
            </p>
          </section>
          <section class="card">
            <h2>Ship to</h2>
            <address>
              <strong>{{ o.shipping_address.name }}</strong> · {{ o.shipping_address.phone }}<br />
              {{ o.shipping_address.line1 }}<br />
              @if (o.shipping_address.line2) {
                {{ o.shipping_address.line2 }}<br />
              }
              @if (o.shipping_address.landmark) {
                Landmark: {{ o.shipping_address.landmark }}<br />
              }
              {{ o.shipping_address.city }}, {{ o.shipping_address.region }}
              {{ o.shipping_address.postal_code }}
            </address>
            @if (o.delivery_instructions) {
              <p><strong>Instructions:</strong> {{ o.delivery_instructions }}</p>
            }
          </section>
          <section class="card">
            <h2>Status history</h2>
            <ol class="timeline">
              @for (e of o.timeline; track $index) {
                <li>
                  <strong>{{ labels[e.to_status] }}</strong>
                  <span class="muted"
                    >{{ e.occurred_at | date: 'dd MMM yyyy, HH:mm' }} ·
                    {{ e.source.toLowerCase() }}</span
                  >
                  @if (e.reason) {
                    <span>{{ e.reason }}</span>
                  }
                </li>
              }
            </ol>
          </section>
        </div>
      </div>
    }
  `,
  styles: `
    .back {
      display: inline-block;
      margin-bottom: var(--space-4);
      font-size: var(--font-size-sm);
    }
    .head {
      display: flex;
      align-items: center;
      gap: var(--space-3);
      flex-wrap: wrap;
    }
    .head h1 {
      margin: 0;
    }
    .muted {
      color: var(--color-muted);
    }
    .grid {
      display: grid;
      grid-template-columns: minmax(0, 1fr) minmax(0, 340px);
      gap: var(--space-6);
      align-items: start;
    }
    .side {
      display: flex;
      flex-direction: column;
      gap: var(--space-4);
    }
    h2 {
      font-size: var(--font-size-md);
      margin: 0 0 var(--space-3);
    }
    section.card {
      overflow-x: auto;
    }
    table {
      width: 100%;
      border-collapse: collapse;
    }
    th,
    td {
      text-align: left;
      padding: var(--space-2);
      border-bottom: 1px solid var(--color-border);
      vertical-align: top;
    }
    .num {
      text-align: right;
    }
    .totals {
      display: grid;
      grid-template-columns: 1fr auto;
      gap: var(--space-2);
      margin: var(--space-4) 0 0;
    }
    .totals dd {
      margin: 0;
      text-align: right;
    }
    .grand {
      font-weight: 700;
    }
    address {
      font-style: normal;
      line-height: 1.6;
    }
    .timeline {
      list-style: none;
      margin: 0;
      padding: 0 0 0 var(--space-4);
      border-left: 2px solid var(--color-border);
    }
    .timeline li {
      display: flex;
      flex-direction: column;
      padding-bottom: var(--space-3);
    }
    @media (max-width: 900px) {
      .grid {
        grid-template-columns: 1fr;
      }
    }
  `,
})
export class OrderDetail {
  private readonly api = inject(AdminOrdersApi);
  readonly id = input.required<string>();
  protected readonly labels = ORDER_STATUS_LABEL;

  protected readonly order = rxResource({
    params: () => this.id(),
    stream: ({ params }) => this.api.order(params),
  });
  protected readonly notFound = computed(() => {
    const err = this.order.error();
    return err instanceof HttpErrorResponse && (err.status === 404 || err.status === 422);
  });
}
