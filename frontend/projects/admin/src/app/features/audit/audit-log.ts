import { DatePipe, JsonPipe } from '@angular/common';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Component, computed, inject, signal } from '@angular/core';
import { rxResource } from '@angular/core/rxjs-interop';
import { FormsModule } from '@angular/forms';
import { API_BASE_URL, Page } from '@shop/shared';

interface AuditEntry {
  id: string;
  occurred_at: string;
  action: string;
  actor_name: string | null;
  actor_email: string | null;
  entity_type: string | null;
  entity_id: string | null;
  before: Record<string, unknown> | null;
  after: Record<string, unknown> | null;
  ip: string | null;
  request_id: string | null;
}

/** "order.status_changed" -> "Order status changed" */
function readable(action: string): string {
  const text = action.replace(/[._]/g, ' ');
  return text.charAt(0).toUpperCase() + text.slice(1);
}

@Component({
  selector: 'adm-audit-log',
  imports: [FormsModule, DatePipe, JsonPipe],
  template: `
    <div class="page-head"><h1>Audit log</h1></div>
    <p class="muted intro">A permanent record of sensitive actions: who did what, and when.</p>

    <form class="filters" (ngSubmit)="apply()">
      <label class="visually-hidden" for="q">Search</label>
      <input
        id="q"
        name="q"
        type="search"
        placeholder="Staff name, email or record id"
        [(ngModel)]="search"
      />
      <label class="visually-hidden" for="action">Action</label>
      <select
        id="action"
        name="action"
        [ngModel]="action()"
        (ngModelChange)="action.set($event); page.set(1)"
      >
        <option value="">All actions</option>
        @for (a of actions.value() ?? []; track a) {
          <option [value]="a">{{ readable(a) }}</option>
        }
      </select>
      <label for="from">From</label>
      <input
        id="from"
        name="from"
        type="date"
        [ngModel]="dateFrom()"
        (ngModelChange)="dateFrom.set($event); page.set(1)"
      />
      <label for="to">To</label>
      <input
        id="to"
        name="to"
        type="date"
        [ngModel]="dateTo()"
        (ngModelChange)="dateTo.set($event); page.set(1)"
      />
      <button class="btn btn-secondary" type="submit">Search</button>
    </form>

    @if (entries.error()) {
      <div class="alert-error" role="alert">
        Couldn't load the audit log.
        <button class="btn btn-secondary" type="button" (click)="entries.reload()">Retry</button>
      </div>
    } @else {
      <div class="card table-wrap">
        <table>
          <thead>
            <tr>
              <th scope="col">When</th>
              <th scope="col">Who</th>
              <th scope="col">Action</th>
              <th scope="col">Record</th>
              <th scope="col"><span class="visually-hidden">Details</span></th>
            </tr>
          </thead>
          <tbody>
            @for (e of entries.value()?.items ?? []; track e.id) {
              <tr>
                <td class="nowrap">{{ e.occurred_at | date: 'dd MMM yyyy, HH:mm:ss' }}</td>
                <td>
                  {{ e.actor_name ?? 'System' }}<br /><small class="muted">{{
                    e.actor_email
                  }}</small>
                </td>
                <td>{{ readable(e.action) }}</td>
                <td>
                  <small>{{ e.entity_type }}</small><br /><small class="muted mono">{{
                    e.entity_id
                  }}</small>
                </td>
                <td>
                  @if (e.before || e.after) {
                    <button
                      class="btn btn-secondary"
                      type="button"
                      [attr.aria-expanded]="open() === e.id"
                      (click)="toggle(e.id)"
                    >
                      {{ open() === e.id ? 'Hide' : 'Changes' }}
                    </button>
                  }
                </td>
              </tr>
              @if (open() === e.id) {
                <tr class="details">
                  <td colspan="5">
                    <div class="diff">
                      @if (e.before) {
                        <div>
                          <strong>Before</strong>
                          <pre>{{ e.before | json }}</pre>
                        </div>
                      }
                      @if (e.after) {
                        <div>
                          <strong>After</strong>
                          <pre>{{ e.after | json }}</pre>
                        </div>
                      }
                    </div>
                    <small class="muted"
                      >IP {{ e.ip ?? '—' }} · request {{ e.request_id ?? '—' }}</small
                    >
                  </td>
                </tr>
              }
            } @empty {
              <tr>
                <td colspan="5" class="empty">
                  {{ entries.isLoading() ? 'Loading…' : 'No entries match.' }}
                </td>
              </tr>
            }
          </tbody>
        </table>
      </div>
      @if (pages() > 1) {
        <nav class="pager" aria-label="Pagination">
          <button
            class="btn btn-secondary"
            type="button"
            [disabled]="page() <= 1"
            (click)="page.set(page() - 1)"
          >
            Previous
          </button>
          <span>Page {{ page() }} of {{ pages() }}</span>
          <button
            class="btn btn-secondary"
            type="button"
            [disabled]="page() >= pages()"
            (click)="page.set(page() + 1)"
          >
            Next
          </button>
        </nav>
      }
    }
  `,
  styleUrl: '../products/admin-table.scss',
  styles: `
    .intro {
      margin-top: calc(-1 * var(--space-2));
    }
    .muted {
      color: var(--color-muted);
    }
    .mono {
      font-family: var(--font-mono);
      overflow-wrap: anywhere;
    }
    .details td {
      background: var(--color-background);
    }
    .diff {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
      gap: var(--space-4);
    }
    pre {
      white-space: pre-wrap;
      overflow-wrap: anywhere;
      font-size: var(--font-size-sm);
      background: var(--color-surface);
      border: 1px solid var(--color-border);
      border-radius: var(--radius-sm);
      padding: var(--space-2);
      margin: var(--space-1) 0 var(--space-2);
    }
  `,
})
export class AuditLog {
  private readonly http = inject(HttpClient);
  private readonly base = `${inject(API_BASE_URL)}/admin/audit-logs`;
  protected readonly readable = readable;

  protected search = '';
  protected readonly q = signal('');
  protected readonly action = signal('');
  protected readonly dateFrom = signal('');
  protected readonly dateTo = signal('');
  protected readonly page = signal(1);
  protected readonly open = signal<string | null>(null);

  protected readonly actions = rxResource({
    stream: () => this.http.get<string[]>(`${this.base}/actions`),
  });
  protected readonly entries = rxResource({
    params: () => ({
      q: this.q(),
      action: this.action(),
      date_from: this.dateFrom(),
      date_to: this.dateTo(),
      page: this.page(),
    }),
    stream: ({ params }) => {
      let p = new HttpParams().set('page', params.page).set('page_size', 50);
      for (const key of ['q', 'action', 'date_from', 'date_to'] as const) {
        if (params[key]) p = p.set(key, params[key]);
      }
      return this.http.get<Page<AuditEntry>>(this.base, { params: p });
    },
  });
  protected readonly pages = computed(() => Math.ceil((this.entries.value()?.total ?? 0) / 50));

  protected apply(): void {
    this.q.set(this.search.trim());
    this.page.set(1);
  }

  protected toggle(id: string): void {
    this.open.set(this.open() === id ? null : id);
  }
}
