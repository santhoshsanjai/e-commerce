import { DatePipe } from '@angular/common';
import { Component, computed, inject, signal } from '@angular/core';
import { rxResource } from '@angular/core/rxjs-interop';
import {
  apiErrorMessage,
  CourierImport,
  CourierImportDetail,
  ImportOutcome,
  ORDER_STATUS_LABEL,
} from '@shop/shared';
import { CourierImportApi } from './courier-import.api';

const OUTCOME_LABEL: Record<ImportOutcome, string> = {
  will_update: 'Will update',
  updated: 'Updated',
  no_change: 'No change',
  error: 'Problem',
};

@Component({
  selector: 'adm-courier-import-page',
  imports: [DatePipe],
  templateUrl: './courier-import-page.html',
  styleUrls: ['../products/admin-table.scss', './courier-import-page.scss'],
})
export class CourierImportPage {
  private readonly api = inject(CourierImportApi);

  protected readonly labels = ORDER_STATUS_LABEL;
  protected readonly outcomes = OUTCOME_LABEL;
  protected readonly page = signal(1);
  protected readonly history = rxResource({
    params: () => this.page(),
    stream: ({ params }) => this.api.imports(params),
  });
  protected readonly historyPages = computed(() => {
    const v = this.history.value();
    return v ? Math.ceil(v.total / v.page_size) : 0;
  });

  protected readonly current = signal<CourierImportDetail | null>(null);
  protected readonly onlyProblems = signal(false);
  protected readonly rows = computed(() => {
    const rows = this.current()?.rows ?? [];
    return this.onlyProblems() ? rows.filter((r) => r.outcome === 'error') : rows;
  });
  protected readonly busy = signal(false);
  protected readonly error = signal<string | null>(null);
  protected readonly message = signal<string | null>(null);

  async onFile(input: HTMLInputElement): Promise<void> {
    const file = input.files?.[0];
    input.value = '';
    if (!file) {
      return;
    }
    await this.run(async () => {
      this.current.set(await this.api.upload(file));
      this.history.reload();
    });
  }

  async confirm(): Promise<void> {
    const current = this.current();
    if (!current) {
      return;
    }
    await this.run(async () => {
      const result = await this.api.confirm(current.id);
      this.current.set(result);
      this.message.set(
        `${result.summary.updated} ${result.summary.updated === 1 ? 'order' : 'orders'} updated.`,
      );
      this.history.reload();
    });
  }

  async downloadErrors(): Promise<void> {
    const current = this.current();
    if (current) {
      await this.run(() => this.api.downloadErrorReport(current));
    }
  }

  async open(item: CourierImport): Promise<void> {
    await this.run(async () => this.current.set(await this.api.get(item.id)));
  }

  private async run(action: () => Promise<void>): Promise<void> {
    this.busy.set(true);
    this.error.set(null);
    this.message.set(null);
    try {
      await action();
    } catch (err) {
      this.error.set(apiErrorMessage(err));
    } finally {
      this.busy.set(false);
    }
  }
}
