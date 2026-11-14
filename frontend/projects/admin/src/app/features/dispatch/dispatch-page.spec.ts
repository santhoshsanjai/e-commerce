import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { AdminOrderListItem } from '@shop/shared';
import { of } from 'rxjs';
import { DispatchApi } from './dispatch.api';
import { DispatchPage } from './dispatch-page';

const order = (id: string, total: number): AdminOrderListItem => ({
  id,
  order_number: `ORD-2026-00000${id}`,
  status: 'CONFIRMED',
  payment_method: 'COD',
  payment_status: 'PENDING',
  total_minor: total,
  currency: 'INR',
  item_count: 1,
  placed_at: '2026-11-14T02:00:00Z',
  customer_name: 'Asha Rao',
  ship_phone: '9876543210',
  ship_city: 'Bengaluru',
});

describe('DispatchPage', () => {
  it('selects all orders, shows the COD total, creates the batch and downloads it', async () => {
    const batch = {
      id: 'b1',
      batch_number: 'DSP-2026-00001',
      order_count: 2,
      file_name: 'DSP-2026-00001.xlsx',
    };
    const api = {
      eligible: vi.fn(() => of([order('1', 10000), order('2', 25050)])),
      batches: vi.fn(() => of({ items: [], total: 0, page: 1, page_size: 10 })),
      create: vi.fn(async () => batch),
      download: vi.fn(async () => undefined),
    };
    TestBed.configureTestingModule({
      imports: [DispatchPage],
      providers: [provideRouter([]), { provide: DispatchApi, useValue: api }],
    });
    const fixture = TestBed.createComponent(DispatchPage);
    await fixture.whenStable();
    const el = fixture.nativeElement as HTMLElement;
    const create = [...el.querySelectorAll('button')].find((b) =>
      b.textContent?.includes('Create batch'),
    )!;
    expect(create.disabled).toBe(true);

    const all = el.querySelector('input[aria-label="Select all orders"]') as HTMLInputElement;
    all.checked = true;
    all.dispatchEvent(new Event('change'));
    await fixture.whenStable();
    expect(el.textContent).toContain('2 selected');
    expect(el.textContent).toContain('₹350.50');

    create.click();
    await fixture.whenStable();
    expect(api.create).toHaveBeenCalledWith(['1', '2']);
    expect(api.download).toHaveBeenCalledWith(batch);
    expect(el.querySelector('[role=status]')?.textContent).toContain('DSP-2026-00001');
  });
});
