import { Component, computed, input, signal } from '@angular/core';
import { MoneyPipe } from '@shop/shared';
import { PeriodRow } from './reports.api';

const MAX_LABELS = 8;

/**
 * Sales per period as columns. One series, so the caption names it and there is no legend.
 * Works from a handful of months up to a year of days: labels thin out so they never collide.
 */
@Component({
  selector: 'adm-period-chart',
  imports: [MoneyPipe],
  template: `
    <figure>
      <figcaption id="period-title">{{ caption() }}</figcaption>
      <div
        class="plot"
        role="group"
        aria-labelledby="period-title period-summary"
        [style.grid-template-columns]="'repeat(' + periods().length + ', minmax(0, 1fr))'"
        [class.dense]="periods().length > 60"
      >
        @for (p of periods(); track p.start; let i = $index) {
          <div
            class="col"
            tabindex="0"
            role="img"
            [attr.aria-label]="p.label + ': ' + (p.sales_minor | money: currency())"
            (mouseenter)="hover.set(i)"
            (mouseleave)="hover.set(null)"
            (focus)="hover.set(i)"
            (blur)="hover.set(null)"
          >
            <div class="track">
              @if (p.sales_minor) {
                <div class="bar" [style.height.%]="(p.sales_minor / max()) * 100"></div>
              }
              @if (hover() === i) {
                <div class="tip" role="tooltip" [class.left]="i > periods().length / 2">
                  <strong>{{ p.label }}</strong>
                  <span>{{ p.sales_minor | money: currency() }}</span>
                  <span>{{ p.orders }} {{ p.orders === 1 ? 'order' : 'orders' }}</span>
                </div>
              }
            </div>
          </div>
        }
      </div>
      <div
        class="axis"
        aria-hidden="true"
        [style.grid-template-columns]="'repeat(' + periods().length + ', minmax(0, 1fr))'"
      >
        @for (p of periods(); track p.start; let i = $index) {
          <span>{{ i % step() === 0 ? short(p.label) : '' }}</span>
        }
      </div>
      <p id="period-summary" class="visually-hidden">
        Total {{ total() | money: currency() }} across {{ periods().length }} periods. Highest
        {{ peak()?.label }} at {{ peak()?.sales_minor ?? 0 | money: currency() }}.
      </p>
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
    .plot,
    .axis {
      display: grid;
      gap: 2px;
    }
    .plot {
      height: 200px;
      border-bottom: 1px solid var(--color-border);
    }
    .plot.dense {
      gap: 0;
    }
    .axis {
      font-size: var(--font-size-sm);
      color: var(--color-muted);
      padding-top: var(--space-1);
      span {
        white-space: nowrap;
        overflow: visible;
        min-width: 0;
      }
    }
    .col {
      display: flex;
      outline: none;
      min-width: 0;
    }
    .col:focus-visible .track {
      box-shadow: var(--focus-ring);
    }
    .track {
      position: relative;
      flex: 1;
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
    .dense .bar {
      border-radius: 1px 1px 0 0;
    }
    .col:hover .bar,
    .col:focus .bar {
      opacity: 0.8;
    }
    .tip {
      position: absolute;
      bottom: 100%;
      left: 0;
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
    .tip.left {
      left: auto;
      right: 0;
    }
  `,
})
export class PeriodChart {
  readonly periods = input.required<PeriodRow[]>();
  readonly currency = input('INR');
  readonly caption = input('Sales');

  protected readonly hover = signal<number | null>(null);
  protected readonly max = computed(() => Math.max(1, ...this.periods().map((p) => p.sales_minor)));
  protected readonly total = computed(() =>
    this.periods().reduce((sum, p) => sum + p.sales_minor, 0),
  );
  protected readonly peak = computed(() =>
    this.periods().reduce<PeriodRow | null>(
      (best, p) => (!best || p.sales_minor > best.sales_minor ? p : best),
      null,
    ),
  );
  /** Show at most MAX_LABELS axis labels. */
  protected readonly step = computed(() =>
    Math.max(1, Math.ceil(this.periods().length / MAX_LABELS)),
  );

  /** "Week of 02 Nov 2026" -> "02 Nov"; "02 Nov 2026" -> "02 Nov"; "Nov 2026" stays. */
  protected short(label: string): string {
    const text = label.replace('Week of ', '');
    const parts = text.split(' ');
    return parts.length === 3 ? `${parts[0]} ${parts[1]}` : text;
  }
}
