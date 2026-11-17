import { HttpClient } from '@angular/common/http';
import { Component, inject, OnInit, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { API_BASE_URL, apiErrorMessage } from '@shop/shared';
import { firstValueFrom } from 'rxjs';

export interface Charges {
  shipping_fee_minor: number;
  free_shipping_over_minor: number | null;
  prices_include_gst: boolean;
  default_gst_rate_bp: number;
}

/** The usual GST slabs, in percent. Any rate from 0 to 40% can be typed in. */
export const GST_SLABS = [0, 5, 18, 40];

/** Rupees as typed (e.g. "49.50") to paise; null for blank, NaN for invalid. */
export function toPaise(value: string | number | null): number | null {
  const text = String(value ?? '').trim();
  if (!text) return null;
  if (!/^\d+(\.\d{1,2})?$/.test(text)) return NaN;
  return Math.round(Number(text) * 100);
}

export function toRupees(paise: number | null): string {
  if (paise === null) return '';
  return paise % 100 === 0 ? String(paise / 100) : (paise / 100).toFixed(2);
}

/** Delivery charge and GST rules for new orders. Placed orders keep their amounts. */
@Component({
  selector: 'adm-charges-page',
  imports: [FormsModule],
  template: `
    <div class="page-head">
      <div>
        <h1>Delivery and GST</h1>
        <p class="muted">
          What buyers pay for delivery, and how GST is worked out. Changes apply to new orders;
          orders already placed keep their amounts.
        </p>
      </div>
    </div>

    <div aria-live="polite">
      @if (notice()) {
        <div class="notice" role="status">{{ notice() }}</div>
      }
      @if (error()) {
        <div class="alert-error" role="alert">{{ error() }}</div>
      }
    </div>

    @if (loading()) {
      <div class="skeleton sk-block" aria-busy="true"></div>
    } @else {
      <form class="card" (ngSubmit)="save()" novalidate>
        <fieldset>
          <legend>Delivery</legend>
          <div class="field">
            <label for="shipping_fee">Delivery charge (₹)</label>
            <input
              id="shipping_fee"
              name="shipping_fee"
              inputmode="decimal"
              [(ngModel)]="shippingFee"
              aria-describedby="shipping_fee_hint"
            />
            <p class="hint" id="shipping_fee_hint">Per order. 0 means delivery is always free.</p>
          </div>
          <div class="field">
            <label for="free_over">Free delivery on orders from (₹)</label>
            <input
              id="free_over"
              name="free_over"
              inputmode="decimal"
              [(ngModel)]="freeOver"
              aria-describedby="free_over_hint"
            />
            <p class="hint" id="free_over_hint">
              Leave blank for no free delivery. Buyers see how much more they need to add.
            </p>
          </div>
        </fieldset>

        <fieldset>
          <legend>GST</legend>
          <div class="choice">
            <label>
              <input type="radio" name="mode" [value]="true" [(ngModel)]="includeGst" />
              Product prices include GST
              <span class="muted"
                >(the usual way in India: the price shown is what buyers pay)</span
              >
            </label>
            <label>
              <input type="radio" name="mode" [value]="false" [(ngModel)]="includeGst" />
              Add GST on top of product prices at checkout
            </label>
          </div>
          <div class="field">
            <label for="gst_rate">Default GST rate (%)</label>
            <input
              id="gst_rate"
              name="gst_rate"
              inputmode="decimal"
              list="gst-slabs"
              [(ngModel)]="gstRate"
              aria-describedby="gst_rate_hint"
            />
            <datalist id="gst-slabs">
              @for (slab of slabs; track slab) {
                <option [value]="slab"></option>
              }
            </datalist>
            <p class="hint" id="gst_rate_hint">
              For products without their own rate. Set a product's own rate on its page.
            </p>
          </div>
        </fieldset>

        <button class="btn" type="submit" [disabled]="saving()">
          {{ saving() ? 'Saving…' : 'Save' }}
        </button>
      </form>
    }
  `,
  styles: `
    form {
      max-width: 560px;
    }
    fieldset {
      border: 0;
      padding: 0;
      margin: 0 0 var(--space-6);
    }
    legend {
      font-weight: 600;
      font-size: var(--font-size-lg);
      margin-bottom: var(--space-3);
    }
    .hint {
      margin: var(--space-1) 0 0;
      font-size: var(--font-size-sm);
      color: var(--color-muted);
    }
    .choice {
      display: grid;
      gap: var(--space-2);
      margin-bottom: var(--space-4);
    }
    .choice label {
      display: flex;
      gap: var(--space-2);
      align-items: baseline;
      flex-wrap: wrap;
    }
  `,
})
export class ChargesPage implements OnInit {
  private readonly http = inject(HttpClient);
  private readonly url = `${inject(API_BASE_URL)}/admin/charges`;

  protected readonly slabs = GST_SLABS;
  protected readonly loading = signal(true);
  protected readonly saving = signal(false);
  protected readonly notice = signal<string | null>(null);
  protected readonly error = signal<string | null>(null);

  protected shippingFee = '';
  protected freeOver = '';
  protected includeGst = true;
  protected gstRate = '';

  async ngOnInit(): Promise<void> {
    try {
      this.accept(await firstValueFrom(this.http.get<Charges>(this.url)));
    } catch (err) {
      this.error.set(apiErrorMessage(err));
    } finally {
      this.loading.set(false);
    }
  }

  protected async save(): Promise<void> {
    this.notice.set(null);
    const fee = toPaise(this.shippingFee) ?? 0;
    const free = toPaise(this.freeOver);
    const rate = Number(String(this.gstRate).trim());
    if (Number.isNaN(fee) || (free !== null && Number.isNaN(free))) {
      this.error.set('Enter amounts in rupees, such as 49 or 49.50.');
      return;
    }
    if (!String(this.gstRate).trim() || Number.isNaN(rate) || rate < 0 || rate > 40) {
      this.error.set('Enter a GST rate from 0 to 40.');
      return;
    }
    if (free !== null && fee === 0) {
      this.error.set('Free delivery from an amount needs a delivery charge to waive.');
      return;
    }
    this.error.set(null);
    this.saving.set(true);
    try {
      const body: Charges = {
        shipping_fee_minor: fee,
        free_shipping_over_minor: free,
        prices_include_gst: this.includeGst,
        default_gst_rate_bp: Math.round(rate * 100),
      };
      this.accept(await firstValueFrom(this.http.put<Charges>(this.url, body)));
      this.notice.set('Saved. New orders use these charges.');
    } catch (err) {
      this.error.set(apiErrorMessage(err));
    } finally {
      this.saving.set(false);
    }
  }

  private accept(c: Charges): void {
    this.shippingFee = toRupees(c.shipping_fee_minor);
    this.freeOver = toRupees(c.free_shipping_over_minor);
    this.includeGst = c.prices_include_gst;
    this.gstRate = String(c.default_gst_rate_bp / 100);
  }
}
