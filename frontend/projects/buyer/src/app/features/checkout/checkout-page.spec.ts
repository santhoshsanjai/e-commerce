import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { signal } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { provideRouter, Router } from '@angular/router';
import { Address, Cart } from '@shop/shared';
import { CartStore } from '../cart/cart.store';
import { CheckoutPage } from './checkout-page';

const CART: Cart = {
  items: [
    {
      sku_id: 'sku-1',
      product_number: 'P-000001',
      product_name: 'Steel Bottle',
      slug: 'steel-bottle',
      image_url: null,
      unit_price_minor: 49950,
      qty: 2,
      line_total_minor: 99900,
      problem: null,
      max_qty: 5,
    },
  ],
  item_count: 2,
  subtotal_minor: 99900,
  shipping_minor: 0,
  total_minor: 99900,
  currency: 'INR',
  can_checkout: true,
};

const ADDRESS: Address = {
  id: 'addr-1',
  recipient_name: 'Asha Rao',
  phone: '9876543210',
  line1: '12 MG Road',
  line2: '',
  landmark: '',
  city: 'Bengaluru',
  region: 'Karnataka',
  postal_code: '560001',
  country_code: 'IN',
  is_default: true,
};

const tick = () => new Promise((r) => setTimeout(r));

describe('CheckoutPage', () => {
  let http: HttpTestingController;
  let fakeCart: {
    cart: ReturnType<typeof signal<Cart | null>>;
    clear: () => void;
    refresh: () => Promise<void>;
  };

  beforeEach(() => {
    fakeCart = {
      cart: signal<Cart | null>(CART),
      clear: vi.fn(),
      refresh: vi.fn(async () => undefined),
    };
    TestBed.configureTestingModule({
      imports: [CheckoutPage],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        provideRouter([]),
        { provide: CartStore, useValue: fakeCart },
      ],
    });
    http = TestBed.inject(HttpTestingController);
  });

  async function render() {
    const fixture = TestBed.createComponent(CheckoutPage);
    await tick();
    http.expectOne('/api/v1/me/addresses').flush([ADDRESS]);
    await fixture.whenStable();
    return fixture;
  }

  it('selects the default address and reuses one idempotency key across retries', async () => {
    const fixture = await render();
    const el = fixture.nativeElement as HTMLElement;
    expect((el.querySelector('input[name=address]') as HTMLInputElement).checked).toBe(true);
    const navigate = vi.spyOn(TestBed.inject(Router), 'navigate').mockResolvedValue(true);

    const place = el.querySelector('button.place') as HTMLButtonElement;
    place.click();
    const first = http.expectOne('/api/v1/checkout');
    expect(first.request.body).toEqual({
      address_id: 'addr-1',
      payment_method: 'COD',
      delivery_instructions: '',
    });
    const key = first.request.headers.get('Idempotency-Key');
    expect(key).toBeTruthy();
    first.error(new ProgressEvent('error'), { status: 0 });
    await fixture.whenStable();
    expect(el.querySelector('[role=alert]')?.textContent).toContain('Cannot reach the server');

    place.click();
    const retry = http.expectOne('/api/v1/checkout');
    expect(retry.request.headers.get('Idempotency-Key')).toBe(key);
    retry.flush({ order_number: 'ORD-2026-000001' });
    await fixture.whenStable();

    expect(fakeCart.clear).toHaveBeenCalled();
    expect(navigate).toHaveBeenCalledWith(['/orders', 'ORD-2026-000001'], {
      queryParams: { placed: 1 },
      replaceUrl: true,
    });
  });

  it('shows the address form when the buyer has no address and blocks a bad PIN code', async () => {
    const fixture = TestBed.createComponent(CheckoutPage);
    await tick();
    http.expectOne('/api/v1/me/addresses').flush([]);
    await fixture.whenStable();
    const el = fixture.nativeElement as HTMLElement;
    expect((el.querySelector('button.place') as HTMLButtonElement).disabled).toBe(true);

    const pin = el.querySelector('#postal_code') as HTMLInputElement;
    pin.value = '012345';
    pin.dispatchEvent(new Event('input'));
    (el.querySelector('.address-form button[type=submit]') as HTMLButtonElement).click();
    await fixture.whenStable();
    expect(el.textContent).toContain('Enter a 6-digit PIN code.');
    http.expectNone('/api/v1/me/addresses');
  });

  afterEach(() => http.verify());
});
