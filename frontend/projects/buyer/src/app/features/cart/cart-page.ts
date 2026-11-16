import { Component, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { apiErrorMessage, CartLine, Icon, MoneyPipe } from '@shop/shared';
import { CartStore } from './cart.store';

const PROBLEM: Record<string, string> = {
  UNAVAILABLE: 'No longer available. Remove it to continue.',
  OUT_OF_STOCK: 'Out of stock. Remove it to continue.',
  INSUFFICIENT_STOCK: 'Not enough stock for this quantity. Lower it to continue.',
};

@Component({
  selector: 'buy-cart-page',
  imports: [RouterLink, MoneyPipe, Icon],
  template: `
    <div class="page-head">
      <span class="eyebrow">Shopping bag</span>
      <h1>Your cart</h1>
    </div>
    @if (error()) {
      <div class="alert-error" role="alert">{{ error() }}</div>
    }
    @if (store.cart(); as cart) {
      @if (cart.items.length === 0) {
        <div class="card empty">
          <shr-icon name="bag" />
          <h2>Your cart is empty</h2>
          <p>Discover something you love in our latest collection.</p>
          <a class="btn" routerLink="/shop">Browse products</a>
        </div>
      } @else {
        <div class="layout">
          <ul class="lines">
            @for (line of cart.items; track line.sku_id) {
              <li [class.busy]="busy()">
                <a class="thumb" [routerLink]="['/products', line.slug]" tabindex="-1">
                  <img [src]="line.image_url" alt="" width="96" height="120" />
                </a>
                <div class="info">
                  <a class="name" [routerLink]="['/products', line.slug]">{{
                    line.product_name
                  }}</a>
                  <span class="muted"
                    >{{ line.product_number }} ·
                    {{ line.unit_price_minor | money: cart.currency }} each</span
                  >
                  @if (line.problem) {
                    <span class="problem" role="alert">{{ problems[line.problem] }}</span>
                  }
                  <div class="qty">
                    <label [for]="'qty-' + line.sku_id"
                      ><span class="visually-hidden">Quantity for {{ line.product_name }}</span
                      ><span aria-hidden="true">Qty</span></label
                    >
                    <select
                      class="select"
                      [id]="'qty-' + line.sku_id"
                      [value]="line.qty"
                      [disabled]="busy()"
                      (change)="setQty(line, $any($event.target).value)"
                    >
                      @for (n of options(line); track n) {
                        <option [value]="n" [selected]="n === line.qty">{{ n }}</option>
                      }
                    </select>
                    <button class="link" type="button" [disabled]="busy()" (click)="remove(line)">
                      Remove
                    </button>
                  </div>
                </div>
                <strong class="total">{{ line.line_total_minor | money: cart.currency }}</strong>
              </li>
            }
          </ul>
          <aside class="card summary" aria-label="Order summary">
            <h2>Order summary</h2>
            <dl>
              <dt>Subtotal</dt>
              <dd>{{ cart.subtotal_minor | money: cart.currency }}</dd>
              <dt>Delivery</dt>
              <dd>
                {{ cart.shipping_minor ? (cart.shipping_minor | money: cart.currency) : 'Free' }}
              </dd>
              <dt class="grand">Total</dt>
              <dd class="grand">{{ cart.total_minor | money: cart.currency }}</dd>
            </dl>
            <a
              class="btn btn-lg btn-block checkout"
              routerLink="/checkout"
              [class.disabled]="!cart.can_checkout"
              [attr.aria-disabled]="!cart.can_checkout"
              (click)="!cart.can_checkout && $event.preventDefault()"
              >Proceed to checkout</a
            >
            <p class="reassure"><shr-icon name="lock" /> Prices include taxes · Secure checkout</p>
            <a class="continue" routerLink="/shop">Continue shopping</a>
          </aside>
        </div>
      }
    } @else {
      <div class="layout" aria-busy="true">
        <div>
          @for (i of [0, 1]; track i) {
            <div class="skeleton sk-line"></div>
          }
        </div>
        <div class="skeleton sk-summary"></div>
      </div>
    }
  `,
  styleUrl: './cart-page.scss',
})
export class CartPage {
  protected readonly store = inject(CartStore);
  protected readonly busy = signal(false);
  protected readonly error = signal<string | null>(null);
  protected readonly problems = PROBLEM;

  protected options(line: CartLine): number[] {
    const max = Math.max(line.max_qty, line.qty);
    return Array.from({ length: max }, (_, i) => i + 1);
  }

  protected setQty(line: CartLine, value: string): Promise<void> {
    return this.run(() => this.store.setQty(line.sku_id, Number(value)));
  }

  protected remove(line: CartLine): Promise<void> {
    return this.run(() => this.store.remove(line.sku_id));
  }

  private async run(action: () => Promise<unknown>): Promise<void> {
    this.busy.set(true);
    this.error.set(null);
    try {
      await action();
    } catch (err) {
      this.error.set(apiErrorMessage(err));
      await this.store.refresh();
    } finally {
      this.busy.set(false);
    }
  }
}
