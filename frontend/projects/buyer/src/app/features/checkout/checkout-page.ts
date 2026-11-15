import { HttpErrorResponse } from '@angular/common/http';
import { Component, computed, inject, linkedSignal, signal } from '@angular/core';
import { rxResource } from '@angular/core/rxjs-interop';
import { NonNullableFormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { Address, apiErrorMessage, MoneyPipe } from '@shop/shared';
import { firstValueFrom } from 'rxjs';
import { AddressForm } from '../account/address-form';
import { CartStore } from '../cart/cart.store';
import { OrdersApi } from '../orders/orders.api';

@Component({
  selector: 'buy-checkout-page',
  imports: [ReactiveFormsModule, RouterLink, MoneyPipe, AddressForm],
  templateUrl: './checkout-page.html',
  styleUrl: './checkout-page.scss',
})
export class CheckoutPage {
  private readonly api = inject(OrdersApi);
  private readonly router = inject(Router);
  protected readonly cartStore = inject(CartStore);

  protected readonly addresses = rxResource({ stream: () => this.api.addresses() });
  protected readonly selectedId = linkedSignal(() => {
    const list = this.addresses.value() ?? [];
    return (list.find((a) => a.is_default) ?? list[0])?.id ?? null;
  });
  protected readonly showForm = linkedSignal(() => this.addresses.value()?.length === 0);

  protected readonly placing = signal(false);
  protected readonly error = signal<string | null>(null);
  protected readonly cartChanged = signal(false);
  protected readonly canPlace = computed(
    () => !!this.selectedId() && !!this.cartStore.cart()?.can_checkout && !this.placing(),
  );

  /** One key per checkout attempt: retrying after a timeout returns the same order. */
  private readonly idempotencyKey = crypto.randomUUID();

  private readonly fb = inject(NonNullableFormBuilder);
  protected readonly instructions = this.fb.control('', Validators.maxLength(500));
  protected oneLine(a: Address): string {
    return [a.line1, a.line2, a.landmark, a.city, `${a.region} ${a.postal_code}`]
      .filter(Boolean)
      .join(', ');
  }

  protected addressSaved(created: Address): void {
    this.addresses.reload();
    this.selectedId.set(created.id);
    this.showForm.set(false);
  }

  async placeOrder(): Promise<void> {
    const addressId = this.selectedId();
    if (!addressId || this.instructions.invalid) {
      return;
    }
    this.placing.set(true);
    this.error.set(null);
    this.cartChanged.set(false);
    try {
      const order = await firstValueFrom(
        this.api.checkout(
          {
            address_id: addressId,
            payment_method: 'COD',
            delivery_instructions: this.instructions.value.trim(),
          },
          this.idempotencyKey,
        ),
      );
      this.cartStore.clear();
      await this.router.navigate(['/orders', order.order_number], {
        queryParams: { placed: 1 },
        replaceUrl: true,
      });
    } catch (err) {
      const conflict = err instanceof HttpErrorResponse && err.status === 409;
      this.cartChanged.set(conflict);
      this.error.set(apiErrorMessage(err));
      if (conflict) {
        await this.cartStore.refresh();
      }
    } finally {
      this.placing.set(false);
    }
  }
}
