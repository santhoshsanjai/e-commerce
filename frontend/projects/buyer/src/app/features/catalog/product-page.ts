import { Component, computed, inject, input, linkedSignal, signal } from '@angular/core';
import { rxResource } from '@angular/core/rxjs-interop';
import { HttpErrorResponse } from '@angular/common/http';
import { Title } from '@angular/platform-browser';
import { Router, RouterLink } from '@angular/router';
import { apiErrorMessage, AuthService, AVAILABILITY_LABEL, Icon, MoneyPipe } from '@shop/shared';
import { tap } from 'rxjs';
import { CartStore } from '../cart/cart.store';
import { CatalogApi } from './catalog.api';

@Component({
  selector: 'buy-product-page',
  imports: [RouterLink, MoneyPipe, Icon],
  templateUrl: './product-page.html',
  styleUrl: './product-page.scss',
})
export class ProductPage {
  private readonly api = inject(CatalogApi);
  private readonly title = inject(Title);
  private readonly auth = inject(AuthService);
  private readonly cart = inject(CartStore);
  private readonly router = inject(Router);

  protected readonly adding = signal(false);
  protected readonly added = signal(false);
  protected readonly cartError = signal<string | null>(null);

  readonly slug = input.required<string>();
  protected readonly labels = AVAILABILITY_LABEL;

  protected readonly product = rxResource({
    params: () => this.slug(),
    stream: ({ params }) => this.api.product(params).pipe(tap((p) => this.title.setTitle(p.name))),
  });
  protected readonly notFound = computed(() => {
    const err = this.product.error();
    return err instanceof HttpErrorResponse && err.status === 404;
  });
  protected readonly selected = linkedSignal(() => {
    const media = this.product.value()?.media ?? [];
    return media.find((m) => m.is_primary) ?? media[0] ?? null;
  });

  protected readonly zoom = signal<string | null>(null);
  protected readonly discount = computed(() => {
    const p = this.product.value();
    if (!p?.compare_at_minor || p.compare_at_minor <= p.price_minor) return 0;
    return Math.round((1 - p.price_minor / p.compare_at_minor) * 100);
  });

  /** Magnify the main image around the pointer (mouse and pen only). */
  protected onZoom(event: PointerEvent): void {
    if (event.pointerType === 'touch') return;
    const box = (event.currentTarget as HTMLElement).getBoundingClientRect();
    const x = ((event.clientX - box.left) / box.width) * 100;
    const y = ((event.clientY - box.top) / box.height) * 100;
    this.zoom.set(`${x.toFixed(1)}% ${y.toFixed(1)}%`);
  }

  async addToCart(skuId: string): Promise<void> {
    if (this.auth.user()?.user_type !== 'BUYER') {
      // ADR 0004: sign-in is required before using the cart.
      await this.router.navigate(['/login'], { queryParams: { returnUrl: this.router.url } });
      return;
    }
    this.adding.set(true);
    this.added.set(false);
    this.cartError.set(null);
    try {
      await this.cart.add(skuId);
      this.added.set(true);
    } catch (err) {
      this.cartError.set(apiErrorMessage(err));
    } finally {
      this.adding.set(false);
    }
  }
}
