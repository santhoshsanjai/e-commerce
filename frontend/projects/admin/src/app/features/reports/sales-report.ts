import { Component, computed, inject, signal } from '@angular/core';
import { rxResource } from '@angular/core/rxjs-interop';
import { FormsModule } from '@angular/forms';
import { apiErrorMessage, MoneyPipe } from '@shop/shared';
import { PeriodChart } from './period-chart';
import { GroupBy, ReportQuery, ReportsApi } from './reports.api';

/** Today's date in India as YYYY-MM-DD; report days are Indian calendar days. */
export function indiaToday(now = new Date()): string {
  return new Intl.DateTimeFormat('en-CA', { timeZone: 'Asia/Kolkata' }).format(now);
}

function shift(iso: string, days: number): string {
  const d = new Date(`${iso}T00:00:00Z`);
  d.setUTCDate(d.getUTCDate() + days);
  return d.toISOString().slice(0, 10);
}

export interface Preset {
  label: string;
  range: (today: string) => Pick<ReportQuery, 'date_from' | 'date_to'>;
}

export const PRESETS: Preset[] = [
  { label: 'Last 7 days', range: (t) => ({ date_from: shift(t, -6), date_to: t }) },
  { label: 'Last 30 days', range: (t) => ({ date_from: shift(t, -29), date_to: t }) },
  { label: 'This month', range: (t) => ({ date_from: `${t.slice(0, 8)}01`, date_to: t }) },
  {
    label: 'Last month',
    range: (t) => {
      const end = shift(`${t.slice(0, 8)}01`, -1);
      return { date_from: `${end.slice(0, 8)}01`, date_to: end };
    },
  },
  { label: 'Last 12 months', range: (t) => ({ date_from: shift(t, -364), date_to: t }) },
];

@Component({
  selector: 'adm-sales-report',
  imports: [FormsModule, MoneyPipe, PeriodChart],
  templateUrl: './sales-report.html',
  styleUrl: './sales-report.scss',
})
export class SalesReport {
  private readonly api = inject(ReportsApi);
  private readonly today = indiaToday();

  protected readonly presets = PRESETS;
  protected readonly query = signal<ReportQuery>({
    ...PRESETS[1].range(this.today),
    group_by: 'day',
  });
  protected readonly rangeError = computed(() => {
    const q = this.query();
    if (!q.date_from || !q.date_to) return 'Choose both dates.';
    return q.date_from > q.date_to ? 'The start date must be on or before the end date.' : null;
  });
  protected readonly report = rxResource({
    // No request while the dates are incomplete or back to front.
    params: () => (this.rangeError() ? undefined : this.query()),
    stream: ({ params }) => this.api.sales(params),
  });
  protected readonly downloading = signal(false);
  protected readonly downloadError = signal<string | null>(null);
  protected readonly activePreset = computed(() => {
    const q = this.query();
    return PRESETS.find((p) => {
      const r = p.range(this.today);
      return r.date_from === q.date_from && r.date_to === q.date_to;
    })?.label;
  });

  protected readonly maxDate = this.today;

  protected orders(n: number): string {
    return `${n} ${n === 1 ? 'order' : 'orders'}`;
  }

  protected errorText(err: unknown): string {
    return `Couldn't load the report. ${apiErrorMessage(err)}`;
  }

  protected applyPreset(p: Preset): void {
    const range = p.range(this.today);
    const days = (Date.parse(range.date_to) - Date.parse(range.date_from)) / 86_400_000 + 1;
    const group_by: GroupBy = days > 92 ? 'month' : days > 31 ? 'week' : 'day';
    this.query.set({ ...range, group_by });
  }

  protected set(change: Partial<ReportQuery>): void {
    this.query.update((q) => ({ ...q, ...change }));
  }

  protected async download(): Promise<void> {
    this.downloading.set(true);
    this.downloadError.set(null);
    try {
      await this.api.download(this.query());
    } catch (err) {
      this.downloadError.set(apiErrorMessage(err));
    } finally {
      this.downloading.set(false);
    }
  }
}
