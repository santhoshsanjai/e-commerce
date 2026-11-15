import { Component, inject, input, OnInit, output, signal } from '@angular/core';
import { NonNullableFormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { Address, AddressInput, apiErrorMessage } from '@shop/shared';
import { firstValueFrom } from 'rxjs';
import { OrdersApi } from '../orders/orders.api';

/** Same rules as the API (ADR 0006): Indian 6-digit PIN code and a phone number. */
const PIN_CODE = /^[1-9][0-9]{5}$/;
const PHONE = /^\+?[0-9][0-9 -]{8,18}[0-9]$/;

/** The editable fields of a saved address. */
export function toInput(a: Address): AddressInput {
  return {
    recipient_name: a.recipient_name,
    phone: a.phone,
    line1: a.line1,
    line2: a.line2,
    landmark: a.landmark,
    city: a.city,
    region: a.region,
    postal_code: a.postal_code,
    is_default: a.is_default,
  };
}

/** Add or edit a delivery address. Used at checkout and on the account page. */
@Component({
  selector: 'buy-address-form',
  imports: [ReactiveFormsModule],
  templateUrl: './address-form.html',
  styleUrl: './address-form.scss',
})
export class AddressForm implements OnInit {
  private readonly api = inject(OrdersApi);
  private readonly fb = inject(NonNullableFormBuilder);

  /** The address to edit; leave out to add a new one. */
  readonly address = input<Address | null>(null);
  readonly heading = input('New address');
  readonly submitLabel = input('Save address');
  readonly cancellable = input(true);
  /** New addresses default to "make default" at checkout, where it is usually the first one. */
  readonly defaultChecked = input(true);

  readonly saved = output<Address>();
  readonly cancelled = output<void>();

  protected readonly saving = signal(false);
  protected readonly error = signal<string | null>(null);

  protected readonly form = this.fb.group({
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

  ngOnInit(): void {
    const a = this.address();
    if (a) {
      this.form.setValue(toInput(a));
    } else {
      this.form.controls.is_default.setValue(this.defaultChecked());
    }
  }

  protected invalid(name: keyof typeof this.form.controls): boolean {
    const c = this.form.controls[name];
    return c.invalid && c.touched;
  }

  protected async save(): Promise<void> {
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      this.error.set('Check the highlighted fields.');
      return;
    }
    this.saving.set(true);
    this.error.set(null);
    try {
      const data = this.form.getRawValue();
      const existing = this.address();
      const result = await firstValueFrom(
        existing ? this.api.updateAddress(existing.id, data) : this.api.createAddress(data),
      );
      this.saved.emit(result);
    } catch (err) {
      this.error.set(apiErrorMessage(err));
    } finally {
      this.saving.set(false);
    }
  }
}
