import { TestBed } from '@angular/core/testing';
import { AdminOrderDetail, AuthService } from '@shop/shared';
import { AdminOrdersApi } from './admin-orders.api';
import { StatusChange } from './status-change';

const ORDER = {
  id: 'o1',
  order_number: 'ORD-2026-000001',
  status: 'CONFIRMED',
  payment_method: 'COD',
  allowed_next: ['CANCELLED', 'EXPORTED_TO_COURIER', 'ON_HOLD', 'READY_FOR_DISPATCH'],
} as unknown as AdminOrderDetail;

const tick = () => new Promise((r) => setTimeout(r));

function setup(canOverride: boolean) {
  const api = { changeStatus: vi.fn(async () => ({ ...ORDER, status: 'CANCELLED' })) };
  TestBed.configureTestingModule({
    imports: [StatusChange],
    providers: [
      { provide: AdminOrdersApi, useValue: api },
      { provide: AuthService, useValue: { hasPermission: () => canOverride } },
    ],
  });
  const fixture = TestBed.createComponent(StatusChange);
  fixture.componentRef.setInput('order', ORDER);
  return { fixture, api, el: fixture.nativeElement as HTMLElement };
}

async function choose(el: HTMLElement, label: string) {
  const select = el.querySelector('select') as HTMLSelectElement;
  const option = [...select.options].find((o) => o.textContent?.trim() === label)!;
  select.value = option.value;
  select.dispatchEvent(new Event('change'));
  await tick();
}

describe('StatusChange', () => {
  it('offers only allowed steps and asks for a reason before cancelling', async () => {
    const { fixture, api, el } = setup(false);
    await fixture.whenStable();
    const labels = [...el.querySelectorAll('option')].map((o) => o.textContent?.trim());
    expect(labels).toEqual([
      'Choose…',
      'Cancelled',
      'Handed to courier',
      'On hold',
      'Ready for dispatch',
    ]);
    expect(el.textContent).not.toContain('Override');

    await choose(el, 'Cancelled');
    fixture.detectChanges();
    expect(el.textContent).toContain('Stock for these items goes back on sale.');
    (el.querySelector('button[type=submit]') as HTMLButtonElement).click();
    await fixture.whenStable();
    expect(el.querySelector('[role=alert]')?.textContent).toContain('reason');
    expect(api.changeStatus).not.toHaveBeenCalled();

    const reason = el.querySelector('#reason') as HTMLInputElement;
    reason.value = 'Buyer asked to cancel';
    reason.dispatchEvent(new Event('input'));
    await tick();
    (el.querySelector('button[type=submit]') as HTMLButtonElement).click();
    await fixture.whenStable();
    expect(api.changeStatus).toHaveBeenCalledWith('o1', {
      status: 'CANCELLED',
      reason: 'Buyer asked to cancel',
      override: false,
    });
  });

  it('lets staff with the override permission pick any status', async () => {
    const { fixture, el } = setup(true);
    await fixture.whenStable();
    const box = el.querySelector('input[type=checkbox]') as HTMLInputElement;
    box.checked = true;
    box.dispatchEvent(new Event('change'));
    await fixture.whenStable();
    const labels = [...el.querySelectorAll('option')].map((o) => o.textContent?.trim());
    expect(labels).toContain('Delivered');
    expect(labels).not.toContain('Confirmed');
  });
});
