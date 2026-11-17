import { DatePipe, NgTemplateOutlet } from '@angular/common';
import { Component, inject, input, signal } from '@angular/core';
import { rxResource } from '@angular/core/rxjs-interop';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import {
  AdminReturn,
  apiErrorMessage,
  HasPermissionDirective,
  Icon,
  MoneyPipe,
  REFUND_METHOD_LABEL,
  RefundMethod,
  RETURN_REASON_LABEL,
  RETURN_STATUS_LABEL,
  toMajorUnits,
  toMinorUnits,
} from '@shop/shared';
import { firstValueFrom, Observable } from 'rxjs';
import { ReturnsApi } from './returns.api';

const MONEY = /^\d{1,9}(\.\d{1,2})?$/;

@Component({
  selector: 'adm-return-detail',
  imports: [
    FormsModule,
    RouterLink,
    DatePipe,
    MoneyPipe,
    HasPermissionDirective,
    Icon,
    NgTemplateOutlet,
  ],
  template: `
    <a routerLink="/returns" class="back"><shr-icon name="chevron-left" /> Returns</a>
    @if (ret.isLoading() && !ret.value()) {
      <div class="skeleton sk-block" aria-busy="true"></div>
    } @else if (ret.error()) {
      <div class="alert-error" role="alert">Couldn't load this return.</div>
    } @else if (ret.value(); as r) {
      <div class="page-head">
        <div>
          <h1>Return {{ r.return_number }}</h1>
          <p class="muted">
            Order <a [routerLink]="['/orders', r.order_id]">{{ r.order_number }}</a> ·
            {{ r.customer_name }} · {{ r.ship_phone }}
          </p>
        </div>
        <span class="chip" [attr.data-status]="r.status">{{ labels[r.status] }}</span>
      </div>

      <div aria-live="polite">
        @if (notice()) {
          <div class="notice" role="status">{{ notice() }}</div>
        }
        @if (error()) {
          <div class="alert-error" role="alert">{{ error() }}</div>
        }
      </div>

      <div class="layout">
        <section class="card">
          <h2>What's coming back</h2>
          <div class="table-wrap">
            <table>
              <thead>
                <tr>
                  <th scope="col">Product</th>
                  <th scope="col" class="num">Qty</th>
                  <th scope="col" class="num">Value</th>
                  <th scope="col">Back in stock</th>
                </tr>
              </thead>
              <tbody>
                @for (i of r.items; track i.order_item_id) {
                  <tr>
                    <td>
                      {{ i.product_name }}<br /><small>{{ i.product_number }}</small>
                    </td>
                    <td class="num">{{ i.qty }}</td>
                    <td class="num">{{ i.unit_price_minor * i.qty | money: r.currency }}</td>
                    <td>{{ r.received_at ? (i.restocked ? 'Yes' : 'No') : '—' }}</td>
                  </tr>
                }
              </tbody>
            </table>
          </div>
          <dl class="facts">
            <dt>Reason</dt>
            <dd>{{ reasons[r.reason] }}</dd>
            @if (r.buyer_note) {
              <dt>Buyer says</dt>
              <dd class="quote">{{ r.buyer_note }}</dd>
            }
            <dt>Asked</dt>
            <dd>{{ r.requested_at | date: 'medium' }}</dd>
            @if (r.decided_at) {
              <dt>Decided</dt>
              <dd>{{ r.decided_at | date: 'medium' }}</dd>
            }
            @if (r.decision_note) {
              <dt>Note to buyer</dt>
              <dd class="quote">{{ r.decision_note }}</dd>
            }
            @if (r.received_at) {
              <dt>Received</dt>
              <dd>{{ r.received_at | date: 'medium' }}</dd>
            }
            @if (r.refunded_at) {
              <dt>Refunded</dt>
              <dd>
                {{ r.refund_minor! | money: r.currency }} by {{ methods[r.refund_method!] }}
                @if (r.refund_reference) {
                  · ref. {{ r.refund_reference }}
                }
                · {{ r.refunded_at | date: 'medium' }}
              </dd>
            }
            <dt>Order total</dt>
            <dd>
              {{ r.order_total_minor | money: r.currency }} · payment
              {{ r.payment_status.toLowerCase() }}
            </dd>
          </dl>
        </section>

        <section class="card" *shrHasPermission="'returns.manage'">
          <h2>Next step</h2>
          @switch (r.status) {
            @case ('REQUESTED') {
              <div class="field">
                <label for="note">Note to the buyer</label>
                <textarea
                  id="note"
                  name="note"
                  rows="4"
                  maxlength="1000"
                  [(ngModel)]="note"
                  placeholder="For approval: how the pickup works. For rejection: why."
                ></textarea>
              </div>
              <div class="buttons">
                <button class="btn" type="button" [disabled]="busy()" (click)="approve(r)">
                  Approve return
                </button>
                <button
                  class="btn btn-secondary"
                  type="button"
                  [disabled]="busy()"
                  (click)="reject(r)"
                >
                  Reject
                </button>
              </div>
            }
            @case ('APPROVED') {
              <div class="action">
                <p>When the parcel is back, tick what can be sold again.</p>
                @for (i of r.items; track i.order_item_id) {
                  <label class="restock">
                    <input
                      type="checkbox"
                      [checked]="restock().has(i.order_item_id)"
                      (change)="toggleRestock(i.order_item_id)"
                    />
                    Put {{ i.qty }} × {{ i.product_name }} back in stock
                  </label>
                }
                <button class="btn" type="button" [disabled]="busy()" (click)="receive(r)">
                  Mark as received
                </button>
              </div>
              <div class="action">
                <ng-container *ngTemplateOutlet="refundForm; context: { $implicit: r }" />
              </div>
            }
            @case ('RECEIVED') {
              <ng-container *ngTemplateOutlet="refundForm; context: { $implicit: r }" />
            }
            @default {
              <p class="muted">Nothing more to do.</p>
            }
          }
        </section>
      </div>

      <ng-template #refundForm let-r>
        @if (r.payment_status === 'PAID') {
          <p>Record the refund once you've paid it (UPI, bank transfer or cash).</p>
          <div class="field">
            <label for="amount">Amount (₹)</label>
            <input
              id="amount"
              inputmode="decimal"
              [(ngModel)]="amount"
              [placeholder]="major(r.items_value_minor)"
            />
            <p class="muted small">Leave blank to refund the items' value.</p>
          </div>
          <div class="field">
            <label for="method">Paid by</label>
            <select id="method" [(ngModel)]="method">
              @for (m of methodKeys; track m) {
                <option [value]="m">{{ methods[m] }}</option>
              }
            </select>
          </div>
          <div class="field">
            <label for="reference">Reference (UTR or transaction no.)</label>
            <input id="reference" maxlength="100" [(ngModel)]="reference" />
          </div>
          <button class="btn" type="button" [disabled]="busy()" (click)="refund(r)">
            Record refund
          </button>
        } @else {
          <p class="muted">
            This order isn't marked paid, so there's nothing to refund. Cash on delivery orders are
            marked paid when delivered.
          </p>
        }
      </ng-template>
    }
  `,
  styleUrls: ['../products/admin-table.scss', './returns.scss'],
})
export class ReturnDetail {
  private readonly api = inject(ReturnsApi);

  readonly id = input.required<string>();

  protected readonly labels = RETURN_STATUS_LABEL;
  protected readonly reasons = RETURN_REASON_LABEL;
  protected readonly methods = REFUND_METHOD_LABEL;
  protected readonly methodKeys = Object.keys(REFUND_METHOD_LABEL) as RefundMethod[];

  protected readonly ret = rxResource({
    params: () => this.id(),
    stream: ({ params }) => this.api.get(params),
  });
  protected readonly busy = signal(false);
  protected readonly error = signal<string | null>(null);
  protected readonly notice = signal<string | null>(null);
  protected readonly restock = signal(new Set<string>());
  protected note = '';
  protected amount = '';
  protected method: RefundMethod = 'UPI';
  protected reference = '';

  protected major(minor: number): string {
    return toMajorUnits(minor);
  }

  protected toggleRestock(id: string): void {
    this.restock.update((s) => {
      const next = new Set(s);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  protected approve(r: AdminReturn): Promise<void> {
    return this.run(
      this.api.approve(r.id, this.note.trim()),
      'Approved. The buyer has been emailed.',
    );
  }

  protected reject(r: AdminReturn): Promise<void> {
    if (this.note.trim().length < 3) {
      this.error.set('Write a note telling the buyer why the return can’t be accepted.');
      return Promise.resolve();
    }
    return this.run(
      this.api.reject(r.id, this.note.trim()),
      'Rejected. The buyer has been emailed.',
    );
  }

  protected receive(r: AdminReturn): Promise<void> {
    return this.run(this.api.receive(r.id, [...this.restock()]), 'Marked as received.');
  }

  protected refund(r: AdminReturn): Promise<void> {
    const text = (this.amount || toMajorUnits(r.items_value_minor)).trim();
    if (!MONEY.test(text)) {
      this.error.set('Enter the amount like 499 or 499.50.');
      return Promise.resolve();
    }
    return this.run(
      this.api.refund(r.id, {
        amount_minor: toMinorUnits(text),
        method: this.method,
        reference: this.reference.trim(),
      }),
      'Refund recorded. The buyer has been emailed.',
    );
  }

  private async run(call: Observable<AdminReturn>, success: string): Promise<void> {
    this.busy.set(true);
    this.error.set(null);
    this.notice.set(null);
    try {
      const updated = await firstValueFrom(call);
      this.ret.set(updated);
      this.notice.set(success);
    } catch (err) {
      this.error.set(apiErrorMessage(err));
    } finally {
      this.busy.set(false);
    }
  }
}
