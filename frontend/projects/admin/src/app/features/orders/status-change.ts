import { Component, computed, inject, input, linkedSignal, output, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import {
  AdminOrderDetail,
  apiErrorMessage,
  AuthService,
  ORDER_STATUS_LABEL,
  OrderStatus,
} from '@shop/shared';
import { AdminOrdersApi } from './admin-orders.api';

/** Needs a reason because staff and buyers see it in the order history. */
const REASON_REQUIRED: OrderStatus[] = ['CANCELLED', 'ON_HOLD'];
const ALL = Object.keys(ORDER_STATUS_LABEL) as OrderStatus[];

@Component({
  selector: 'adm-status-change',
  imports: [FormsModule],
  template: `
    <section class="card" aria-labelledby="status-h">
      <h2 id="status-h">Change status</h2>
      @if (error()) {
        <div class="alert-error" role="alert">{{ error() }}</div>
      }
      @if (options().length === 0) {
        <p class="muted">
          This order is {{ labels[order().status].toLowerCase() }}. No further steps.
        </p>
      }
      @if (canOverride()) {
        <label class="check">
          <input type="checkbox" [(ngModel)]="override" name="override" />
          Override the usual order of steps
        </label>
      }
      @if (options().length) {
        <form (ngSubmit)="save()">
          <div class="field">
            <label for="next-status">New status</label>
            <select id="next-status" name="status" [(ngModel)]="target" required>
              <option [ngValue]="null" disabled>Choose…</option>
              @for (s of options(); track s) {
                <option [ngValue]="s">{{ labels[s] }}</option>
              }
            </select>
          </div>
          <div class="field">
            <label for="reason">Reason {{ reasonNeeded() ? '' : '(optional)' }}</label>
            <input id="reason" name="reason" maxlength="500" [(ngModel)]="reason" />
            @if (cancelBeforeHandover()) {
              <small class="muted">Stock for these items goes back on sale.</small>
            }
            @if (target() === 'DELIVERED' && order().payment_method === 'COD') {
              <small class="muted">Cash on delivery will be marked as collected.</small>
            }
          </div>
          <button class="btn" type="submit" [disabled]="!target() || saving()">
            {{ saving() ? 'Saving…' : 'Update status' }}
          </button>
        </form>
      }
    </section>
  `,
  styles: `
    h2 {
      font-size: var(--font-size-md);
      margin: 0 0 var(--space-3);
    }
    .muted {
      color: var(--color-muted);
      font-size: var(--font-size-sm);
      display: block;
      margin-top: var(--space-1);
    }
    .check {
      display: flex;
      gap: var(--space-2);
      align-items: center;
      margin-bottom: var(--space-3);
      font-size: var(--font-size-sm);
    }
  `,
})
export class StatusChange {
  private readonly api = inject(AdminOrdersApi);
  private readonly auth = inject(AuthService);

  readonly order = input.required<AdminOrderDetail>();
  readonly changed = output<AdminOrderDetail>();

  protected readonly labels = ORDER_STATUS_LABEL;
  protected readonly canOverride = computed(() =>
    this.auth.hasPermission('orders.status.override'),
  );
  protected readonly override = signal(false);
  protected readonly options = computed(() => {
    const o = this.order();
    return this.override() ? ALL.filter((s) => s !== o.status) : o.allowed_next;
  });
  protected readonly target = linkedSignal<OrderStatus[], OrderStatus | null>({
    source: () => this.options(),
    computation: () => null,
  });
  protected readonly reason = signal('');
  protected readonly reasonNeeded = computed(() => {
    const t = this.target();
    return this.override() || (t !== null && REASON_REQUIRED.includes(t));
  });
  protected readonly cancelBeforeHandover = computed(
    () =>
      this.target() === 'CANCELLED' &&
      ['PENDING_CONFIRMATION', 'CONFIRMED', 'READY_FOR_DISPATCH', 'ON_HOLD'].includes(
        this.order().status,
      ),
  );
  protected readonly saving = signal(false);
  protected readonly error = signal<string | null>(null);

  async save(): Promise<void> {
    const target = this.target();
    if (!target) {
      return;
    }
    if (this.reasonNeeded() && this.reason().trim().length < 3) {
      this.error.set('Give a short reason for this change.');
      return;
    }
    this.saving.set(true);
    this.error.set(null);
    try {
      const updated = await this.api.changeStatus(this.order().id, {
        status: target,
        reason: this.reason().trim(),
        override: this.override() && !this.order().allowed_next.includes(target),
      });
      this.reason.set('');
      this.override.set(false);
      this.changed.emit(updated);
    } catch (err) {
      this.error.set(apiErrorMessage(err));
    } finally {
      this.saving.set(false);
    }
  }
}
