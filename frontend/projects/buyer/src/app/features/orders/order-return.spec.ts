import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { OrderDetail, ReturnEligibility } from '@shop/shared';
import { OrderReturn } from './order-return';

const ORDER = {
  order_number: 'ORD-2026-000001',
  items: [
    {
      id: 'item-1',
      product_number: 'P-000001',
      product_name: 'Steel Bottle',
      sku: 'P-000001',
      unit_price_minor: 49950,
      qty: 2,
      line_total_minor: 99900,
      gst_rate_bp: 1800,
      gst_minor: 15239,
    },
  ],
} as unknown as OrderDetail;

const URL = '/api/v1/me/orders/ORD-2026-000001/return';

describe('OrderReturn', () => {
  async function setup(state: ReturnEligibility) {
    TestBed.configureTestingModule({
      imports: [OrderReturn],
      providers: [provideHttpClient(), provideHttpClientTesting()],
    });
    const fixture = TestBed.createComponent(OrderReturn);
    fixture.componentRef.setInput('order', ORDER);
    const http = TestBed.inject(HttpTestingController);
    fixture.detectChanges();
    http.expectOne(URL).flush(state);
    await fixture.whenStable();
    fixture.detectChanges();
    return { fixture, http, el: fixture.nativeElement as HTMLElement };
  }

  it('asks for a return of the chosen items', async () => {
    const { fixture, http, el } = await setup({
      can_request: true,
      deadline: '2026-11-24T10:00:00Z',
      reason_not: '',
      current: null,
    });
    expect(el.textContent).toContain('You can ask to return items until');
    el.querySelector<HTMLButtonElement>('.return button')!.click();
    await fixture.whenStable();
    fixture.detectChanges();

    // Nothing chosen yet.
    el.querySelector<HTMLButtonElement>('button[type=submit]')!.click();
    await fixture.whenStable();
    fixture.detectChanges();
    expect(el.querySelector('[role=alert]')!.textContent).toContain('Choose at least one item');
    http.expectNone({ method: 'POST', url: URL });

    el.querySelector<HTMLInputElement>('input[type=checkbox]')!.click();
    await fixture.whenStable();
    fixture.detectChanges();
    el.querySelector<HTMLButtonElement>('button[type=submit]')!.click();
    const req = http.expectOne({ method: 'POST', url: URL });
    expect(req.request.body).toEqual({
      items: [{ order_item_id: 'item-1', qty: 2 }],
      reason: 'DAMAGED',
      note: '',
    });
  });

  it('shows the return in progress and lets the buyer withdraw it', async () => {
    const { http, el } = await setup({
      can_request: false,
      deadline: '2026-11-24T10:00:00Z',
      reason_not: 'A return for this order is already in progress.',
      current: {
        return_number: 'RET-2026-000001',
        order_number: 'ORD-2026-000001',
        status: 'REQUESTED',
        reason: 'DAMAGED',
        buyer_note: '',
        decision_note: '',
        items: [
          {
            order_item_id: 'item-1',
            product_number: 'P-000001',
            product_name: 'Steel Bottle',
            qty: 1,
            unit_price_minor: 49950,
            restocked: false,
          },
        ],
        items_value_minor: 49950,
        refund_minor: null,
        refund_method: null,
        refund_reference: '',
        currency: 'INR',
        requested_at: '2026-11-17T10:00:00Z',
        decided_at: null,
        received_at: null,
        refunded_at: null,
      },
    });
    expect(el.textContent).toContain('Return RET-2026-000001');
    expect(el.textContent).toContain('Requested');
    el.querySelector<HTMLButtonElement>('.return button')!.click();
    http.expectOne({ method: 'POST', url: '/api/v1/me/returns/RET-2026-000001/withdraw' });
  });
});
