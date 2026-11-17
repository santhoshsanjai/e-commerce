import { DatePipe } from '@angular/common';
import { Component, inject, input, output, signal } from '@angular/core';
import { rxResource } from '@angular/core/rxjs-interop';
import { FormsModule } from '@angular/forms';
import {
  apiErrorMessage,
  MoneyPipe,
  OrderDetail,
  REFUND_METHOD_LABEL,
  RETURN_REASON_LABEL,
  RETURN_STATUS_LABEL,
  ReturnReason,
} from '@shop/shared';
import { firstValueFrom } from 'rxjs';
import { OrdersApi } from './orders.api';

/** Return items from a delivered order, and follow the return once asked for. */
@Component({
  selector: 'buy-order-return',
  imports: [FormsModule, DatePipe, MoneyPipe],
  template: `
    @if (state.value(); as st) {
      @if (st.current; as r) {
        <section class="card return" aria-labelledby="return-title">
          <h3 id="return-title">Return {{ r.return_number }}</h3>
          <p>
            <strong class="return-status">{{ statusLabel[r.status] }}</strong>
            <span class="muted"> · asked {{ r.requested_at | date: 'mediumDate' }}</span>
          </p>
          <ul class="plain">
            @for (i of r.items; track i.order_item_id) {
              <li>{{ i.qty }} × {{ i.product_name }}</li>
            }
          </ul>
          @if (r.decision_note) {
            <p class="note">{{ r.decision_note }}</p>
          }
          @if (r.status === 'REFUNDED' && r.refund_minor) {
            <p>
              Refunded {{ r.refund_minor | money: r.currency }} by
              {{ methodLabel[r.refund_method!] }}
              @if (r.refund_reference) {
                (reference {{ r.refund_reference }})
              }
            </p>
          }
          @if (r.status === 'REQUESTED') {
            <button
              class="btn btn-secondary"
              type="button"
              [disabled]="busy()"
              (click)="withdraw(r.return_number)"
            >
              Withdraw this request
            </button>
          }
        </section>
      }
      @if (st.can_request) {
        <section class="card return" aria-labelledby="return-form-title">
          <h3 id="return-form-title">Return items</h3>
          @if (!open()) {
            <p class="muted">
              You can ask to return items until {{ st.deadline | date: 'mediumDate' }}.
            </p>
            <button class="btn btn-secondary" type="button" (click)="open.set(true)">
              Start a return
            </button>
          } @else {
            <form (ngSubmit)="submit()" novalidate>
              <fieldset>
                <legend>Which items?</legend>
                @for (item of order().items; track item.id) {
                  <div class="return-line">
                    <label>
                      <input
                        type="checkbox"
                        [name]="'pick-' + item.id"
                        [ngModel]="picked()[item.id] !== undefined"
                        (ngModelChange)="toggle(item.id, item.qty, $event)"
                      />
                      {{ item.product_name }}
                    </label>
                    @if (picked()[item.id] !== undefined && item.qty > 1) {
                      <label class="qty">
                        <span class="visually-hidden">How many of {{ item.product_name }}</span>
                        <select
                          [name]="'qty-' + item.id"
                          [ngModel]="picked()[item.id]"
                          (ngModelChange)="setQty(item.id, $event)"
                        >
                          @for (n of range(item.qty); track n) {
                            <option [ngValue]="n">{{ n }}</option>
                          }
                        </select>
                      </label>
                    }
                  </div>
                }
              </fieldset>
              <div class="field">
                <label for="return-reason">Why are you returning them?</label>
                <select id="return-reason" name="reason" [(ngModel)]="reason">
                  @for (r of reasons; track r) {
                    <option [value]="r">{{ reasonLabel[r] }}</option>
                  }
                </select>
              </div>
              <div class="field">
                <label for="return-note">Anything we should know? (optional)</label>
                <textarea
                  id="return-note"
                  name="note"
                  rows="3"
                  maxlength="1000"
                  [(ngModel)]="note"
                ></textarea>
              </div>
              @if (error()) {
                <div class="alert-error" role="alert">{{ error() }}</div>
              }
              <button class="btn" type="submit" [disabled]="busy()">
                {{ busy() ? 'Sending…' : 'Ask for a return' }}
              </button>
            </form>
          }
        </section>
      } @else if (!st.current && st.reason_not && st.deadline) {
        <p class="muted small">{{ st.reason_not }}</p>
      }
    }
  `,
  styleUrl: './orders.scss',
})
export class OrderReturn {
  private readonly api = inject(OrdersApi);

  readonly order = input.required<OrderDetail>();
  readonly changed = output<void>();

  protected readonly statusLabel = RETURN_STATUS_LABEL;
  protected readonly reasonLabel = RETURN_REASON_LABEL;
  protected readonly methodLabel = REFUND_METHOD_LABEL;
  protected readonly reasons = Object.keys(RETURN_REASON_LABEL) as ReturnReason[];

  protected readonly state = rxResource({
    params: () => this.order().order_number,
    stream: ({ params }) => this.api.returnStatus(params),
  });
  protected readonly open = signal(false);
  protected readonly busy = signal(false);
  protected readonly error = signal<string | null>(null);
  /** Order item id -> quantity to return. */
  protected readonly picked = signal<Record<string, number>>({});
  protected reason: ReturnReason = 'DAMAGED';
  protected note = '';

  protected range(n: number): number[] {
    return Array.from({ length: n }, (_, i) => i + 1);
  }

  protected toggle(id: string, max: number, on: boolean): void {
    this.picked.update((p) => {
      const next = { ...p };
      if (on) next[id] = max;
      else delete next[id];
      return next;
    });
  }

  protected setQty(id: string, qty: number): void {
    this.picked.update((p) => ({ ...p, [id]: Number(qty) }));
  }

  protected async submit(): Promise<void> {
    const items = Object.entries(this.picked()).map(([order_item_id, qty]) => ({
      order_item_id,
      qty,
    }));
    if (!items.length) {
      this.error.set('Choose at least one item to return.');
      return;
    }
    await this.run(() =>
      firstValueFrom(
        this.api.requestReturn(this.order().order_number, {
          items,
          reason: this.reason,
          note: this.note.trim(),
        }),
      ),
    );
    this.open.set(false);
  }

  protected async withdraw(returnNumber: string): Promise<void> {
    await this.run(() => firstValueFrom(this.api.withdrawReturn(returnNumber)));
  }

  private async run(action: () => Promise<unknown>): Promise<void> {
    this.busy.set(true);
    this.error.set(null);
    try {
      await action();
      this.state.reload();
      this.changed.emit();
    } catch (err) {
      this.error.set(apiErrorMessage(err));
    } finally {
      this.busy.set(false);
    }
  }
}
