import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { AuthService } from '@shop/shared';
import { of } from 'rxjs';
import { Dashboard } from './dashboard';
import { DashboardApi, DashboardData } from './dashboard.api';

const days = Array.from({ length: 7 }, (_, i) => ({
  day: `2026-11-${String(9 + i).padStart(2, '0')}`,
  orders: i,
  sales_minor: i * 10000,
}));

const DATA = {
  currency: 'INR',
  today: days[6],
  last_7_days: days,
  cod_with_courier_minor: 250000,
  status_counts: { CONFIRMED: 3, ON_HOLD: 1 },
  attention: {
    awaiting_dispatch: 3,
    delivery_failed: 0,
    on_hold: 1,
    returning: 0,
    imports_not_applied: 0,
    low_stock: [{ product_id: 'p1', product_number: 'P-000001', name: 'Mug', stock_qty: 2 }],
  },
} as unknown as DashboardData;

function setup(granted: string[]) {
  TestBed.configureTestingModule({
    imports: [Dashboard],
    providers: [
      provideRouter([]),
      { provide: DashboardApi, useValue: { load: () => of(DATA) } },
      {
        provide: AuthService,
        useValue: { hasPermission: (k: string) => granted.includes(k), user: () => null },
      },
    ],
  });
  const fixture = TestBed.createComponent(Dashboard);
  return fixture;
}

describe('Dashboard', () => {
  it('shows today, the week, and what needs attention with links the user may follow', async () => {
    const fixture = setup(['orders.export', 'orders.view']);
    await fixture.whenStable();
    const el = fixture.nativeElement as HTMLElement;
    const tiles = [...el.querySelectorAll('.tile-value')].map((t) => t.textContent?.trim());
    expect(tiles).toEqual(['6', '₹600.00', '₹2,100.00', '₹2,500.00']);
    expect(el.textContent).toContain('3 confirmed orders are waiting to go to the courier');
    expect(el.querySelector('a[href="/dispatch"]')).not.toBeNull();
    expect(el.textContent).toContain('Low stock: Mug');
    // No products.view, so no edit link.
    expect(el.querySelector('a[href="/products/p1"]')).toBeNull();
    expect(el.querySelectorAll('.col').length).toBe(7);
  });
});
