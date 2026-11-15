import { TestBed } from '@angular/core/testing';
import { of } from 'rxjs';
import { ReportsApi, SalesReport as Report } from './reports.api';
import { indiaToday, PRESETS, SalesReport } from './sales-report';

const preset = (label: string) => PRESETS.find((p) => p.label === label)!;

describe('report date helpers', () => {
  it('uses the Indian calendar day', () => {
    // 20:00 UTC on 14 Nov is 01:30 on 15 Nov in India.
    expect(indiaToday(new Date('2026-11-14T20:00:00Z'))).toBe('2026-11-15');
  });

  it('works out the quick ranges', () => {
    expect(preset('Last 7 days').range('2026-11-15')).toEqual({
      date_from: '2026-11-09',
      date_to: '2026-11-15',
    });
    expect(preset('This month').range('2026-11-15')).toEqual({
      date_from: '2026-11-01',
      date_to: '2026-11-15',
    });
    expect(preset('Last month').range('2026-03-10')).toEqual({
      date_from: '2026-02-01',
      date_to: '2026-02-28',
    });
  });
});

describe('SalesReport', () => {
  it('loads the last 30 days, switches range and downloads with the same filters', async () => {
    const report: Report = {
      currency: 'INR',
      date_from: '2026-10-17',
      date_to: '2026-11-15',
      group_by: 'day',
      summary: {
        orders: 2,
        sales_minor: 35050,
        avg_order_minor: 17525,
        items_sold: 3,
        delivered_orders: 1,
        delivered_minor: 10000,
        cod_collected_minor: 10000,
        cancelled_orders: 0,
        cancelled_minor: 0,
        returned_orders: 0,
        returned_minor: 0,
      },
      periods: [
        { start: '2026-11-15', label: '15 Nov 2026', orders: 2, sales_minor: 35050, items_sold: 3 },
      ],
      top_products: [{ product_number: 'P-1', product_name: 'Mug', qty: 3, sales_minor: 35050 }],
      regions: [{ region: 'Karnataka', orders: 2, sales_minor: 35050 }],
    };
    const api = { sales: vi.fn(() => of(report)), download: vi.fn(async () => undefined) };
    TestBed.configureTestingModule({
      imports: [SalesReport],
      providers: [{ provide: ReportsApi, useValue: api }],
    });
    const fixture = TestBed.createComponent(SalesReport);
    await fixture.whenStable();
    const el = fixture.nativeElement as HTMLElement;

    const first = api.sales.mock.calls[0] as unknown as [{ date_from: string; date_to: string }];
    const days = (Date.parse(first[0].date_to) - Date.parse(first[0].date_from)) / 86_400_000;
    expect(days).toBe(29);
    expect(el.textContent).toContain('₹350.50');
    expect(el.textContent).toContain('Karnataka');

    const twelve = [...el.querySelectorAll('button')].find((b) =>
      b.textContent?.includes('Last 12 months'),
    )!;
    twelve.click();
    await fixture.whenStable();
    expect(twelve.getAttribute('aria-pressed')).toBe('true');
    const latest = api.sales.mock.calls.at(-1) as unknown as [{ group_by: string }];
    expect(latest[0].group_by).toBe('month');

    const download = [...el.querySelectorAll('button')].find((b) =>
      b.textContent?.includes('Download Excel'),
    )!;
    download.click();
    await fixture.whenStable();
    expect(api.download).toHaveBeenCalledWith(latest[0]);
  });
});
