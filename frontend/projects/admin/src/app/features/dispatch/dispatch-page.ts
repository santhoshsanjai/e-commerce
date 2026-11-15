import { DatePipe } from '@angular/common';
import { Component, computed, inject, linkedSignal, signal } from '@angular/core';
import { rxResource } from '@angular/core/rxjs-interop';
import { RouterLink } from '@angular/router';
import { apiErrorMessage, DispatchBatch, MoneyPipe } from '@shop/shared';
import { DispatchApi } from './dispatch.api';

@Component({
  selector: 'adm-dispatch-page',
  imports: [RouterLink, MoneyPipe, DatePipe],
  template: `
    <div class="page-head">
      <h1>Dispatch</h1>
    </div>

    @if (message()) {
      <div class="alert-success" role="status">{{ message() }}</div>
    }
    @if (error()) {
      <div class="alert-error" role="alert">{{ error() }}</div>
    }

    <section aria-labelledby="ready-h">
      <div class="section-head">
        <h2 id="ready-h">Ready to dispatch</h2>
        @if (selectedCount()) {
          <span class="muted">
            {{ selectedCount() }} selected · COD to collect
            {{ selectedCod() | money: 'INR' }}
          </span>
        }
        <button
          class="btn"
          type="button"
          [disabled]="!selectedCount() || creating()"
          (click)="createBatch()"
        >
          {{ creating() ? 'Creating…' : 'Create batch and download Excel' }}
        </button>
      </div>

      @if (eligible.error()) {
        <div class="alert-error" role="alert">
          Couldn't load orders.
          <button class="btn btn-secondary" type="button" (click)="eligible.reload()">Retry</button>
        </div>
      } @else {
        <div class="card table-wrap">
          <table>
            <thead>
              <tr>
                <th scope="col" class="check">
                  <input
                    type="checkbox"
                    aria-label="Select all orders"
                    [checked]="allSelected()"
                    [indeterminate]="selectedCount() > 0 && !allSelected()"
                    [disabled]="!eligible.value()?.length"
                    (change)="toggleAll($any($event.target).checked)"
                  />
                </th>
                <th scope="col">Order no.</th>
                <th scope="col">Placed</th>
                <th scope="col">Customer</th>
                <th scope="col">City</th>
                <th scope="col" class="num">Items</th>
                <th scope="col" class="num">COD amount</th>
              </tr>
            </thead>
            <tbody>
              @for (o of eligible.value() ?? []; track o.id) {
                <tr [class.selected]="selected().has(o.id)">
                  <td class="check">
                    <input
                      type="checkbox"
                      [attr.aria-label]="'Select ' + o.order_number"
                      [checked]="selected().has(o.id)"
                      (change)="toggle(o.id)"
                    />
                  </td>
                  <td class="nowrap">
                    <a [routerLink]="['/orders', o.id]">{{ o.order_number }}</a>
                  </td>
                  <td>{{ o.placed_at | date: 'dd MMM yyyy, HH:mm' }}</td>
                  <td>
                    {{ o.customer_name }}<br /><small>{{ o.ship_phone }}</small>
                  </td>
                  <td>{{ o.ship_city }}</td>
                  <td class="num">{{ o.item_count }}</td>
                  <td class="num">{{ o.total_minor | money: o.currency }}</td>
                </tr>
              } @empty {
                <tr>
                  <td colspan="7" class="empty">
                    {{
                      eligible.isLoading()
                        ? 'Loading…'
                        : 'No confirmed orders waiting for dispatch.'
                    }}
                  </td>
                </tr>
              }
            </tbody>
          </table>
        </div>
      }
    </section>

    <section aria-labelledby="batches-h">
      <h2 id="batches-h">Recent batches</h2>
      <div class="card table-wrap">
        <table>
          <thead>
            <tr>
              <th scope="col">Batch</th>
              <th scope="col">Created</th>
              <th scope="col">By</th>
              <th scope="col" class="num">Orders</th>
              <th scope="col" class="num">COD total</th>
              <th scope="col"><span class="visually-hidden">File</span></th>
            </tr>
          </thead>
          <tbody>
            @for (b of batches.value()?.items ?? []; track b.id) {
              <tr>
                <td class="nowrap">{{ b.batch_number }}</td>
                <td>{{ b.created_at | date: 'dd MMM yyyy, HH:mm' }}</td>
                <td>{{ b.created_by_name ?? '—' }}</td>
                <td class="num">{{ b.order_count }}</td>
                <td class="num">{{ b.cod_total_minor | money: b.currency }}</td>
                <td>
                  <button class="btn btn-secondary" type="button" (click)="download(b)">
                    Download Excel
                  </button>
                </td>
              </tr>
            } @empty {
              <tr>
                <td colspan="6" class="empty">
                  {{ batches.isLoading() ? 'Loading…' : 'No batches yet.' }}
                </td>
              </tr>
            }
          </tbody>
        </table>
      </div>
      @if (batchPages() > 1) {
        <nav class="pager" aria-label="Batch pages">
          <button
            class="btn btn-secondary"
            type="button"
            [disabled]="page() <= 1"
            (click)="page.set(page() - 1)"
          >
            Previous
          </button>
          <span>Page {{ page() }} of {{ batchPages() }}</span>
          <button
            class="btn btn-secondary"
            type="button"
            [disabled]="page() >= batchPages()"
            (click)="page.set(page() + 1)"
          >
            Next
          </button>
        </nav>
      }
    </section>
  `,
  styleUrls: ['../products/admin-table.scss', './dispatch-page.scss'],
})
export class DispatchPage {
  private readonly api = inject(DispatchApi);

  protected readonly eligible = rxResource({ stream: () => this.api.eligible() });
  protected readonly page = signal(1);
  protected readonly batches = rxResource({
    params: () => this.page(),
    stream: ({ params }) => this.api.batches(params),
  });
  protected readonly batchPages = computed(() => {
    const v = this.batches.value();
    return v ? Math.ceil(v.total / v.page_size) : 0;
  });

  /** Reset whenever the list reloads, so a stale selection can't be submitted. */
  protected readonly selected = linkedSignal<unknown, Set<string>>({
    source: () => this.eligible.value(),
    computation: () => new Set(),
  });
  protected readonly selectedCount = computed(() => this.selected().size);
  protected readonly allSelected = computed(() => {
    const list = this.eligible.value() ?? [];
    return list.length > 0 && this.selected().size === list.length;
  });
  protected readonly selectedCod = computed(() =>
    (this.eligible.value() ?? [])
      .filter((o) => this.selected().has(o.id) && o.payment_method === 'COD')
      .reduce((sum, o) => sum + o.total_minor, 0),
  );

  protected readonly creating = signal(false);
  protected readonly message = signal<string | null>(null);
  protected readonly error = signal<string | null>(null);

  protected toggle(id: string): void {
    const next = new Set(this.selected());
    if (!next.delete(id)) {
      next.add(id);
    }
    this.selected.set(next);
  }

  protected toggleAll(checked: boolean): void {
    this.selected.set(new Set(checked ? (this.eligible.value() ?? []).map((o) => o.id) : []));
  }

  async createBatch(): Promise<void> {
    this.creating.set(true);
    this.error.set(null);
    this.message.set(null);
    try {
      const batch = await this.api.create([...this.selected()]);
      this.message.set(
        `Batch ${batch.batch_number} created with ${batch.order_count} ${batch.order_count === 1 ? 'order' : 'orders'}. ` +
          'They are now marked as handed to the courier.',
      );
      this.eligible.reload();
      this.page.set(1);
      this.batches.reload();
      await this.api.download(batch);
    } catch (err) {
      this.error.set(apiErrorMessage(err));
      this.eligible.reload();
    } finally {
      this.creating.set(false);
    }
  }

  async download(batch: DispatchBatch): Promise<void> {
    this.error.set(null);
    try {
      await this.api.download(batch);
    } catch (err) {
      this.error.set(apiErrorMessage(err, 'Could not download the file. Please try again.'));
    }
  }
}
