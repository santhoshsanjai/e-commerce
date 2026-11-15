import { HttpClient } from '@angular/common/http';
import { computed, effect, inject, Injectable, signal, untracked } from '@angular/core';
import { API_BASE_URL, AuthService, Cart } from '@shop/shared';
import { firstValueFrom } from 'rxjs';

/** The signed-in buyer's cart, kept in sync with the server (the source of truth). */
@Injectable({ providedIn: 'root' })
export class CartStore {
  private readonly http = inject(HttpClient);
  private readonly base = `${inject(API_BASE_URL)}/cart`;
  private readonly auth = inject(AuthService);

  private readonly state = signal<Cart | null>(null);
  readonly cart = this.state.asReadonly();
  readonly count = computed(() => this.state()?.item_count ?? 0);

  constructor() {
    // Load the cart on sign-in, clear it on sign-out.
    effect(() => {
      const user = this.auth.user();
      untracked(() => {
        if (user?.user_type === 'BUYER') {
          // A failed background load only hides the count; the cart page retries and shows errors.
          this.refresh().catch(() => this.state.set(null));
        } else {
          this.state.set(null);
        }
      });
    });
  }

  async refresh(): Promise<Cart> {
    return this.apply(this.http.get<Cart>(this.base));
  }

  add(skuId: string, qty = 1): Promise<Cart> {
    return this.apply(this.http.post<Cart>(`${this.base}/items`, { sku_id: skuId, qty }));
  }

  setQty(skuId: string, qty: number): Promise<Cart> {
    return this.apply(this.http.patch<Cart>(`${this.base}/items/${skuId}`, { qty }));
  }

  remove(skuId: string): Promise<Cart> {
    return this.apply(this.http.delete<Cart>(`${this.base}/items/${skuId}`));
  }

  /** Called after checkout empties the cart on the server. */
  clear(): void {
    this.refresh().catch(() => this.state.set(null));
  }

  private async apply(request: ReturnType<HttpClient['get']>): Promise<Cart> {
    const cart = (await firstValueFrom(request)) as Cart;
    this.state.set(cart);
    return cart;
  }
}
