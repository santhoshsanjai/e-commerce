import { Component, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { apiErrorMessage, CartLine, MoneyPipe } from '@shop/shared';
import { CartStore } from './cart.store';

const PROBLEM: Record<string, string> = {
  UNAVAILABLE: 'No longer available. Remove it to continue.',
  OUT_OF_STOCK: 'Out of stock. Remove it to continue.',
  INSUFFICIENT_STOCK: 'Not enough stock for this quantity. Lower it to continue.',
};

@Component({
  selector: 'buy-cart-page',
  imports: [RouterLink, MoneyPipe],
  template: `
    <h1>Your cart</h1>
    @if (error()) {
      <div class="alert-error" role="alert">{{ error() }}</div>
    }
    @if (store.cart(); as cart) {
      @if (cart.items.length === 0) {
        <div class="card empty">
          <p>Your cart is empty.</p>
          <a class="btn" routerLink="/">Browse products</a>
        </div>
      } @else {
        <div class="layout">
          <ul class="lines card">
            @for (line of cart.items; track line.sku_id) {
              <li>
                <img [src]="line.image_url" alt="" width="72" height="72" />
                <div class="info">
                  <a [routerLink]="['/products', line.slug]">{{ line.product_name }}</a>
                  <span class="muted"
                    >{{ line.product_number }} ·
                    {{ line.unit_price_minor | money: cart.currency }} each</span
                  >
                  @if (line.problem) {
                    <span class="problem" role="alert">{{ problems[line.problem] }}</span>
                  }
                </div>
                <div class="qty">
                  <label class="visually-hidden" [for]="'qty-' + line.sku_id"
                    >Quantity for {{ line.product_name }}</label
                  >
                  <select
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
                <strong class="total">{{ line.line_total_minor | money: cart.currency }}</strong>
              </li>
            }
          </ul>
          <aside class="card summary" aria-label="Order summary">
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
              class="btn checkout"
              routerLink="/checkout"
              [class.disabled]="!cart.can_checkout"
              [attr.aria-disabled]="!cart.can_checkout"
              (click)="!cart.can_checkout && $event.preventDefault()"
              >Proceed to checkout</a
            >
            <p class="muted small">Prices include taxes.</p>
          </aside>
        </div>
      }
    } @else {
      <p aria-busy="true">Loading your cart…</p>
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
