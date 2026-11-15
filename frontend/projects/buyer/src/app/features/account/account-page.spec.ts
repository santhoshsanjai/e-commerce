import { signal } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { Address, AuthService, Me } from '@shop/shared';
import { of } from 'rxjs';
import { OrdersApi } from '../orders/orders.api';
import { AccountPage } from './account-page';

const ME: Me = {
  id: 'u1',
  email: 'neha@example.com',
  full_name: 'Neha',
  phone: null,
  user_type: 'BUYER',
  roles: [],
  permissions: [],
  mfa_enabled: false,
};

const address = (id: string, city: string, isDefault: boolean): Address => ({
  id,
  recipient_name: 'Neha',
  phone: '9876543210',
  line1: '12 MG Road',
  line2: '',
  landmark: '',
  city,
  region: 'Karnataka',
  postal_code: '560001',
  country_code: 'IN',
  is_default: isDefault,
});

async function setup() {
  const user = signal<Me | null>(ME);
  const auth = {
    user,
    updateProfile: vi.fn(async (data: Partial<Me>) => {
      user.set({ ...ME, ...data });
      return user()!;
    }),
    changePassword: vi.fn(async () => undefined),
  };
  const api = {
    addresses: vi.fn(() => of([address('a1', 'Bengaluru', true), address('a2', 'Mysuru', false)])),
    updateAddress: vi.fn(() => of(address('a2', 'Mysuru', true))),
    deleteAddress: vi.fn(() => of(undefined)),
    createAddress: vi.fn(),
  };
  TestBed.configureTestingModule({
    imports: [AccountPage],
    providers: [
      { provide: AuthService, useValue: auth },
      { provide: OrdersApi, useValue: api },
    ],
  });
  const fixture = TestBed.createComponent(AccountPage);
  await fixture.whenStable();
  const el = fixture.nativeElement as HTMLElement;
  const button = (text: string) =>
    [...el.querySelectorAll('button')].find((b) => b.textContent?.trim().startsWith(text));
  const type = async (id: string, value: string) => {
    const input = el.querySelector(`#${id}`) as HTMLInputElement;
    input.value = value;
    input.dispatchEvent(new Event('input'));
    await fixture.whenStable();
  };
  return { auth, api, fixture, el, button, type };
}

describe('AccountPage', () => {
  it('saves name and phone', async () => {
    const { auth, el, button, type, fixture } = await setup();
    expect(button('Save details')!.disabled).toBe(true);
    await type('profile_name', 'Neha Sharma');
    await type('profile_phone', '+91 98765 43210');
    button('Save details')!.click();
    await fixture.whenStable();
    expect(auth.updateProfile).toHaveBeenCalledWith({
      full_name: 'Neha Sharma',
      phone: '+91 98765 43210',
    });
    expect(el.textContent).toContain('Your details are saved.');
  });

  it('makes an address the default and removes one after confirming', async () => {
    const { api, button, fixture } = await setup();
    button('Make default')!.click();
    await fixture.whenStable();
    expect(api.updateAddress).toHaveBeenCalledWith(
      'a2',
      expect.objectContaining({ city: 'Mysuru', is_default: true }),
    );

    button('Remove')!.click();
    await fixture.whenStable();
    expect(api.deleteAddress).not.toHaveBeenCalled();
    button('Yes, remove')!.click();
    await fixture.whenStable();
    expect(api.deleteAddress).toHaveBeenCalledWith('a1');
  });

  it('opens the edit form filled in with the address', async () => {
    const { el, button, fixture } = await setup();
    button('Edit')!.click();
    await fixture.whenStable();
    expect((el.querySelector('#city') as HTMLInputElement).value).toBe('Bengaluru');
    expect(el.textContent).toContain('Edit address');
  });

  it('only changes the password when the new one is long enough and typed twice', async () => {
    const { auth, el, button, type, fixture } = await setup();
    await type('current_password', 'old-password');
    await type('new_password', 'brand-new-pass');
    await type('confirm_password', 'brand-new-pas');
    expect(button('Change password')!.disabled).toBe(true);
    expect(el.textContent).toContain("The two new passwords don't match.");

    await type('confirm_password', 'brand-new-pass');
    button('Change password')!.click();
    await fixture.whenStable();
    expect(auth.changePassword).toHaveBeenCalledWith('old-password', 'brand-new-pass');
    expect(el.textContent).toContain('signed out on your other devices');
  });
});
