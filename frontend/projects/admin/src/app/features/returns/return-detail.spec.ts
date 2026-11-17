import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { AdminReturn, AuthService } from '@shop/shared';
import { of } from 'rxjs';
import { ReturnDetail } from './return-detail';
import { ReturnsApi } from './returns.api';

const BASE: AdminReturn = {
  id: 'r1',
  return_number: 'RET-2026-000001',
  order_number: 'ORD-2026-000001',
  order_id: 'o1',
  order_status: 'DELIVERED',
  payment_status: 'PAID',
  order_total_minor: 99900,
  customer_name: 'Asha Rao',
  customer_email: 'asha@example.com',
  ship_phone: '9876543210',
  status: 'REQUESTED',
  reason: 'DAMAGED',
  buyer_note: 'Cracked lid',
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
};

describe('ReturnDetail', () => {
  function setup(ret: AdminReturn) {
    const api = {
      get: vi.fn(() => of(ret)),
      approve: vi.fn(() => of({ ...ret, status: 'APPROVED' })),
      reject: vi.fn(() => of({ ...ret, status: 'REJECTED' })),
      receive: vi.fn(() => of({ ...ret, status: 'RECEIVED' })),
      refund: vi.fn(() => of({ ...ret, status: 'REFUNDED', refund_minor: 49950 })),
    };
    TestBed.configureTestingModule({
      imports: [ReturnDetail],
      providers: [
        provideRouter([]),
        { provide: ReturnsApi, useValue: api },
        { provide: AuthService, useValue: { hasPermission: () => true, user: () => null } },
      ],
    });
    const fixture = TestBed.createComponent(ReturnDetail);
    fixture.componentRef.setInput('id', 'r1');
    return { fixture, api, el: fixture.nativeElement as HTMLElement };
  }

  async function settle(fixture: { detectChanges(): void; whenStable(): Promise<unknown> }) {
    fixture.detectChanges();
    await fixture.whenStable();
    fixture.detectChanges();
  }

  function button(el: HTMLElement, text: string): HTMLButtonElement {
    return [...el.querySelectorAll('button')].find((b) => b.textContent!.includes(text))!;
  }

  it('needs a note to reject, then approves with the note', async () => {
    const { fixture, api, el } = setup(BASE);
    await settle(fixture);
    expect(el.textContent).toContain('Cracked lid');
    button(el, 'Reject').click();
    await settle(fixture);
    expect(api.reject).not.toHaveBeenCalled();
    expect(el.querySelector('[role=alert]')!.textContent).toContain('why');

    const note = el.querySelector<HTMLTextAreaElement>('#note')!;
    note.value = 'Courier picks up Monday';
    note.dispatchEvent(new Event('input'));
    button(el, 'Approve return').click();
    await settle(fixture);
    expect(api.approve).toHaveBeenCalledWith('r1', 'Courier picks up Monday');
    expect(el.textContent).toContain('Approved');
  });

  it('restocks the ticked items and refunds the items value by default', async () => {
    const { fixture, api, el } = setup({ ...BASE, status: 'APPROVED' });
    await settle(fixture);
    el.querySelector<HTMLInputElement>('.restock input')!.click();
    button(el, 'Mark as received').click();
    await settle(fixture);
    expect(api.receive).toHaveBeenCalledWith('r1', ['item-1']);

    button(el, 'Record refund').click();
    await settle(fixture);
    expect(api.refund).toHaveBeenCalledWith('r1', {
      amount_minor: 49950,
      method: 'UPI',
      reference: '',
    });
  });
});
