import { DatePipe } from '@angular/common';
import { Component, computed, input, signal } from '@angular/core';
import { MoneyPipe } from '@shop/shared';
import { DaySales } from './dashboard.api';

/** Seven-day sales as columns. One series, so the title names it and there is no legend. */
@Component({
  selector: 'adm-sales-chart',
  imports: [DatePipe, MoneyPipe],
  template: `
    <figure>
      <figcaption id="sales-title">Sales, last 7 days</figcaption>
      <div class="plot" role="group" aria-labelledby="sales-title sales-summary">
        @for (d of days(); track d.day; let i = $index) {
          <div
            class="col"
            tabindex="0"
            role="img"
            [attr.aria-label]="
              (d.day | date: 'EEE d MMM') + ': ' + (d.sales_minor | money: currency())
            "
            (mouseenter)="hover.set(i)"
            (mouseleave)="hover.set(null)"
            (focus)="hover.set(i)"
            (blur)="hover.set(null)"
          >
            <div class="track">
              @if (d.sales_minor) {
                <div class="bar" [style.height.%]="(d.sales_minor / max()) * 100"></div>
              }
              @if (hover() === i) {
                <div class="tip" role="tooltip">
                  <strong>{{ d.day | date: 'EEE d MMM' }}</strong>
                  <span>{{ d.sales_minor | money: currency() }}</span>
                  <span>{{ d.orders }} {{ d.orders === 1 ? 'order' : 'orders' }}</span>
                </div>
              }
            </div>
            <span class="label">{{ d.day | date: 'EEE' }}</span>
          </div>
        }
      </div>
      <p id="sales-summary" class="visually-hidden">
        Total {{ total() | money: currency() }} over 7 days.
      </p>
      <details>
        <summary>Show as table</summary>
        <table>
          <thead>
            <tr>
              <th scope="col">Day</th>
              <th scope="col" class="num">Orders</th>
              <th scope="col" class="num">Sales</th>
            </tr>
          </thead>
          <tbody>
            @for (d of days(); track d.day) {
              <tr>
                <td>{{ d.day | date: 'EEE d MMM' }}</td>
                <td class="num">{{ d.orders }}</td>
                <td class="num">{{ d.sales_minor | money: currency() }}</td>
              </tr>
            }
          </tbody>
        </table>
      </details>
    </figure>
  `,
  styles: `
    figure {
      margin: 0;
    }
    figcaption {
      font-weight: 600;
      margin-bottom: var(--space-3);
    }
    .plot {
      display: grid;
      grid-template-columns: repeat(7, 1fr);
      gap: 2px;
      height: 160px;
      border-bottom: 1px solid var(--color-border);
    }
    .col {
      display: flex;
      flex-direction: column;
      align-items: center;
      outline: none;
      cursor: default;
      min-width: 0;
    }
    .col:focus-visible .track {
      box-shadow: var(--focus-ring);
    }
    .track {
      position: relative;
      flex: 1;
      width: 100%;
      display: flex;
      align-items: flex-end;
      justify-content: center;
    }
    .bar {
      width: 100%;
      max-width: 24px;
      min-height: 2px;
      background: var(--color-primary);
      border-radius: 4px 4px 0 0;
    }
    .col:hover .bar,
    .col:focus .bar {
      opacity: 0.85;
    }
    .label {
      font-size: var(--font-size-sm);
      color: var(--color-muted);
      padding-top: var(--space-1);
      transform: translateY(100%);
    }
    .tip {
      position: absolute;
      bottom: 100%;
      left: 50%;
      transform: translateX(-50%);
      z-index: 1;
      display: flex;
      flex-direction: column;
      gap: 2px;
      padding: var(--space-2) var(--space-3);
      background: var(--color-surface);
      color: var(--color-text);
      border: 1px solid var(--color-border);
      border-radius: var(--radius-md);
      box-shadow: 0 4px 12px rgb(0 0 0 / 12%);
      font-size: var(--font-size-sm);
      white-space: nowrap;
      pointer-events: none;
    }
    details {
      margin-top: var(--space-8);
      font-size: var(--font-size-sm);
    }
    summary {
      cursor: pointer;
      color: var(--color-primary);
    }
    table {
      width: 100%;
      border-collapse: collapse;
      margin-top: var(--space-2);
    }
    th,
    td {
      text-align: left;
      padding: var(--space-1) var(--space-2);
      border-bottom: 1px solid var(--color-border);
    }
    .num {
      text-align: right;
    }
  `,
})
export class SalesChart {
  readonly days = input.required<DaySales[]>();
  readonly currency = input('INR');
  protected readonly hover = signal<number | null>(null);
  protected readonly max = computed(() => Math.max(1, ...this.days().map((d) => d.sales_minor)));
  protected readonly total = computed(() => this.days().reduce((s, d) => s + d.sales_minor, 0));
}
