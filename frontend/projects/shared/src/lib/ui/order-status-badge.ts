import { Component, computed, input } from '@angular/core';
import { ORDER_STATUS_LABEL, OrderStatus } from '../models/order.models';

const TONE: Partial<Record<OrderStatus, 'good' | 'bad' | 'warn'>> = {
  DELIVERED: 'good',
  COMPLETED: 'good',
  CANCELLED: 'bad',
  DELIVERY_FAILED: 'bad',
  RETURNED: 'bad',
  RETURN_IN_TRANSIT: 'warn',
  ON_HOLD: 'warn',
};

/** Order status as a small pill, shared by the buyer and admin apps. */
@Component({
  selector: 'shr-order-status',
  template: `<span class="badge" [class]="tone()">{{ label() }}</span>`,
  styles: `
    .badge {
      display: inline-block;
      padding: 2px var(--space-2);
      border-radius: 999px;
      font-size: var(--font-size-sm);
      font-weight: 600;
      white-space: nowrap;
      color: var(--color-primary);
      border: 1px solid currentColor;
    }
    .good {
      color: var(--color-success);
    }
    .bad {
      color: var(--color-danger);
    }
    .warn {
      color: var(--color-warning);
    }
  `,
})
export class OrderStatusBadge {
  readonly status = input.required<OrderStatus>();
  protected readonly label = computed(() => ORDER_STATUS_LABEL[this.status()]);
  protected readonly tone = computed(() => `badge ${TONE[this.status()] ?? ''}`);
}
