import { Component, computed, inject, linkedSignal, signal } from '@angular/core';
import { rxResource } from '@angular/core/rxjs-interop';
import { FormsModule } from '@angular/forms';
import { Address, apiErrorMessage, AuthService } from '@shop/shared';
import { firstValueFrom } from 'rxjs';
import { OrdersApi } from '../orders/orders.api';
import { AddressForm, toInput } from './address-form';

const MIN_PASSWORD = 10;

/** "Editing" is an address id, 'new' for the add form, or null when no form is open. */
type Editing = string | 'new' | null;

@Component({
  selector: 'buy-account-page',
  imports: [FormsModule, AddressForm],
  templateUrl: './account-page.html',
  styleUrl: './account-page.scss',
})
export class AccountPage {
  private readonly auth = inject(AuthService);
  private readonly api = inject(OrdersApi);

  protected readonly user = this.auth.user;
  protected readonly minPassword = MIN_PASSWORD;

  // Your details
  protected readonly fullName = linkedSignal(() => this.user()?.full_name ?? '');
  protected readonly phone = linkedSignal(() => this.user()?.phone ?? '');
  protected readonly profileBusy = signal(false);
  protected readonly profileNotice = signal<string | null>(null);
  protected readonly profileError = signal<string | null>(null);
  protected readonly profileChanged = computed(
    () =>
      this.fullName().trim() !== (this.user()?.full_name ?? '') ||
      this.phone().trim() !== (this.user()?.phone ?? ''),
  );

  // Addresses
  protected readonly addresses = rxResource({ stream: () => this.api.addresses() });
  protected readonly editing = signal<Editing>(null);
  protected readonly confirmingDelete = signal<string | null>(null);
  protected readonly addressNotice = signal<string | null>(null);
  protected readonly addressError = signal<string | null>(null);

  // Password
  protected currentPassword = '';
  protected newPassword = '';
  protected confirmPassword = '';
  protected readonly passwordBusy = signal(false);
  protected readonly passwordNotice = signal<string | null>(null);
  protected readonly passwordError = signal<string | null>(null);

  protected oneLine(a: Address): string {
    return [a.line1, a.line2, a.landmark, a.city, `${a.region} ${a.postal_code}`]
      .filter(Boolean)
      .join(', ');
  }

  protected async saveProfile(): Promise<void> {
    if (!this.fullName().trim()) {
      this.profileError.set('Enter your name.');
      return;
    }
    this.profileBusy.set(true);
    this.profileNotice.set(null);
    this.profileError.set(null);
    try {
      await this.auth.updateProfile({
        full_name: this.fullName().trim(),
        phone: this.phone().trim(),
      });
      this.profileNotice.set('Your details are saved.');
    } catch (err) {
      this.profileError.set(apiErrorMessage(err));
    } finally {
      this.profileBusy.set(false);
    }
  }

  protected startEdit(target: Editing): void {
    this.editing.set(target);
    this.confirmingDelete.set(null);
    this.addressNotice.set(null);
    this.addressError.set(null);
  }

  protected addressSaved(): void {
    this.addressNotice.set(this.editing() === 'new' ? 'Address added.' : 'Address updated.');
    this.editing.set(null);
    this.addresses.reload();
  }

  protected async makeDefault(a: Address): Promise<void> {
    await this.addressAction(async () => {
      await firstValueFrom(this.api.updateAddress(a.id, { ...toInput(a), is_default: true }));
      return `${a.recipient_name}, ${a.city} is now your default address.`;
    });
  }

  protected async remove(a: Address): Promise<void> {
    await this.addressAction(async () => {
      await firstValueFrom(this.api.deleteAddress(a.id));
      return 'Address removed.';
    });
  }

  private async addressAction(action: () => Promise<string>): Promise<void> {
    this.addressNotice.set(null);
    this.addressError.set(null);
    this.confirmingDelete.set(null);
    try {
      this.addressNotice.set(await action());
      this.addresses.reload();
    } catch (err) {
      this.addressError.set(apiErrorMessage(err));
    }
  }

  protected passwordProblem(): string | null {
    if (!this.currentPassword || !this.newPassword) return null;
    if (this.newPassword.length < MIN_PASSWORD) {
      return `Your new password needs at least ${MIN_PASSWORD} characters.`;
    }
    if (this.confirmPassword && this.confirmPassword !== this.newPassword) {
      return "The two new passwords don't match.";
    }
    return null;
  }

  protected canChangePassword(): boolean {
    return (
      !this.passwordBusy() &&
      !!this.currentPassword &&
      this.newPassword.length >= MIN_PASSWORD &&
      this.newPassword === this.confirmPassword
    );
  }

  protected async changePassword(): Promise<void> {
    if (!this.canChangePassword()) return;
    this.passwordBusy.set(true);
    this.passwordNotice.set(null);
    this.passwordError.set(null);
    try {
      await this.auth.changePassword(this.currentPassword, this.newPassword);
      this.currentPassword = this.newPassword = this.confirmPassword = '';
      this.passwordNotice.set(
        "Password changed. You're still signed in here and signed out on your other devices.",
      );
    } catch (err) {
      this.passwordError.set(apiErrorMessage(err));
    } finally {
      this.passwordBusy.set(false);
    }
  }
}
