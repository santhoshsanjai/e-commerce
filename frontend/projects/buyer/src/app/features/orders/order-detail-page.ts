import { HttpErrorResponse } from '@angular/common/http';
import { Component, computed, inject, input } from '@angular/core';
import { rxResource } from '@angular/core/rxjs-interop';
import { DatePipe } from '@angular/common';
import { RouterLink } from '@angular/router';
import { MoneyPipe, ORDER_STATUS_LABEL, OrderStatusBadge } from '@shop/shared';
import { OrdersApi } from './orders.api';

@Component({
  selector: 'buy-order-detail-page',
  imports: [RouterLink, MoneyPipe, DatePipe, OrderStatusBadge],
  template: `
    <a routerLink="/orders" class="back">← My orders</a>
    @if (order.isLoading()) {
      <p aria-busy="true">Loading…</p>
    } @else if (notFound()) {
      <h1>Order not found</h1>
      <p>Check the order number, or see <a routerLink="/orders">all your orders</a>.</p>
    } @else if (order.error()) {
      <div class="alert-error" role="alert">
        We couldn't load this order.
        <button class="btn btn-secondary" type="button" (click)="order.reload()">Try again</button>
      </div>
    } @else if (order.value(); as o) {
      @if (justPlaced()) {
        <div class="card thanks" role="status">
          <h1>Thank you, your order is placed</h1>
          <p>
            Your order number is <strong>{{ o.order_number }}</strong>. Please keep
            {{ o.total_minor | money: o.currency }} ready to pay in cash on delivery.
          </p>
        </div>
      }
      <div class="head">
        @if (justPlaced()) {
          <h2>Order {{ o.order_number }}</h2>
        } @else {
          <h1>Order {{ o.order_number }}</h1>
        }
        <shr-order-status [status]="o.status" />
      </div>
      <p class="muted">Placed {{ o.placed_at | date: 'medium' }} · Cash on delivery</p>

      <div class="layout">
        <section class="card">
          <h3>Items</h3>
          <ul class="items">
            @for (item of o.items; track item.sku) {
              <li>
                <span>
                  {{ item.product_name }}
                  <span class="muted"
                    >{{ item.product_number }} · {{ item.unit_price_minor | money: o.currency }} ×
                    {{ item.qty }}</span
                  >
                </span>
                <strong>{{ item.line_total_minor | money: o.currency }}</strong>
              </li>
            }
          </ul>
          <dl class="totals">
            <dt>Subtotal</dt>
            <dd>{{ o.subtotal_minor | money: o.currency }}</dd>
            <dt>Delivery</dt>
            <dd>{{ o.shipping_minor ? (o.shipping_minor | money: o.currency) : 'Free' }}</dd>
            @if (o.discount_minor) {
              <dt>Discount</dt>
              <dd>−{{ o.discount_minor | money: o.currency }}</dd>
            }
            <dt class="grand">Total</dt>
            <dd class="grand">{{ o.total_minor | money: o.currency }}</dd>
          </dl>
        </section>

        <div class="side">
          <section class="card">
            <h3>Delivering to</h3>
            <address>
              <strong>{{ o.shipping_address.name }}</strong><br />
              {{ o.shipping_address.line1 }}<br />
              @if (o.shipping_address.line2) {
                {{ o.shipping_address.line2 }}<br />
              }
              @if (o.shipping_address.landmark) {
                Near {{ o.shipping_address.landmark }}<br />
              }
              {{ o.shipping_address.city }}, {{ o.shipping_address.region }}
              {{ o.shipping_address.postal_code }}<br />
              {{ o.shipping_address.phone }}
            </address>
            @if (o.delivery_instructions) {
              <p class="muted">Note: {{ o.delivery_instructions }}</p>
            }
          </section>
          <section class="card">
            <h3>Progress</h3>
            <ol class="timeline">
              @for (e of o.timeline; track $index) {
                <li>
                  <strong>{{ labels[e.to_status] }}</strong>
                  <span class="muted">{{ e.occurred_at | date: 'medium' }}</span>
                </li>
              }
            </ol>
          </section>
        </div>
      </div>
    }
  `,
  styleUrl: './orders.scss',
})
export class OrderDetailPage {
  private readonly api = inject(OrdersApi);

  readonly orderNumber = input.required<string>();
  /** Set to "1" by checkout so the page doubles as the order confirmation. */
  readonly placed = input<string>();
  protected readonly justPlaced = computed(() => this.placed() === '1');
  protected readonly labels = ORDER_STATUS_LABEL;

  protected readonly order = rxResource({
    params: () => this.orderNumber(),
    stream: ({ params }) => this.api.myOrder(params),
  });
  protected readonly notFound = computed(() => {
    const err = this.order.error();
    return err instanceof HttpErrorResponse && err.status === 404;
  });
}
