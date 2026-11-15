import { TestBed } from '@angular/core/testing';
import { OrderStatusBadge } from './order-status-badge';

describe('OrderStatusBadge', () => {
  it('shows a readable label and a tone for the status', async () => {
    const fixture = TestBed.createComponent(OrderStatusBadge);
    fixture.componentRef.setInput('status', 'CANCELLED');
    await fixture.whenStable();
    const badge = (fixture.nativeElement as HTMLElement).querySelector('span')!;
    expect(badge.textContent).toBe('Cancelled');
    expect(badge.classList).toContain('bad');
  });
});
