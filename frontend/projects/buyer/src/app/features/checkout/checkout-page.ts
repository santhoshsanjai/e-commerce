import { HttpErrorResponse } from '@angular/common/http';
import { Component, computed, inject, linkedSignal, signal } from '@angular/core';
import { rxResource } from '@angular/core/rxjs-interop';
import { NonNullableFormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { Address, apiErrorMessage, MoneyPipe } from '@shop/shared';
import { firstValueFrom } from 'rxjs';
import { CartStore } from '../cart/cart.store';
import { OrdersApi } from '../orders/orders.api';

/** Same rules as the API (ADR 0006): Indian 6-digit PIN code and a phone number. */
const PIN_CODE = /^[1-9][0-9]{5}$/;
const PHONE = /^\+?[0-9][0-9 -]{8,18}[0-9]$/;

@Component({
  selector: 'buy-checkout-page',
  imports: [ReactiveFormsModule, RouterLink, MoneyPipe],
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
  protected readonly savingAddress = signal(false);
  protected readonly error = signal<string | null>(null);
  protected readonly cartChanged = signal(false);
  protected readonly addressError = signal<string | null>(null);
  protected readonly canPlace = computed(
    () => !!this.selectedId() && !!this.cartStore.cart()?.can_checkout && !this.placing(),
  );

  /** One key per checkout attempt: retrying after a timeout returns the same order. */
  private readonly idempotencyKey = crypto.randomUUID();

  private readonly fb = inject(NonNullableFormBuilder);
  protected readonly instructions = this.fb.control('', Validators.maxLength(500));
  protected readonly addressForm = this.fb.group({
    recipient_name: ['', [Validators.required, Validators.maxLength(200)]],
    phone: ['', [Validators.required, Validators.pattern(PHONE)]],
    line1: ['', [Validators.required, Validators.maxLength(200)]],
    line2: ['', Validators.maxLength(200)],
    landmark: ['', Validators.maxLength(200)],
    city: ['', [Validators.required, Validators.maxLength(100)]],
    region: ['', [Validators.required, Validators.maxLength(100)]],
    postal_code: ['', [Validators.required, Validators.pattern(PIN_CODE)]],
    is_default: [true],
  });

  protected invalid(name: keyof typeof this.addressForm.controls): boolean {
    const c = this.addressForm.controls[name];
    return c.invalid && c.touched;
  }

  protected oneLine(a: Address): string {
    return [a.line1, a.line2, a.landmark, a.city, `${a.region} ${a.postal_code}`]
      .filter(Boolean)
      .join(', ');
  }

  async saveAddress(): Promise<void> {
    if (this.addressForm.invalid) {
      this.addressForm.markAllAsTouched();
      this.addressError.set('Check the highlighted fields.');
      return;
    }
    this.savingAddress.set(true);
    this.addressError.set(null);
    try {
      const created = await firstValueFrom(this.api.createAddress(this.addressForm.getRawValue()));
      this.addresses.reload();
      this.selectedId.set(created.id);
      this.showForm.set(false);
      this.addressForm.reset();
    } catch (err) {
      this.addressError.set(apiErrorMessage(err));
    } finally {
      this.savingAddress.set(false);
    }
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
