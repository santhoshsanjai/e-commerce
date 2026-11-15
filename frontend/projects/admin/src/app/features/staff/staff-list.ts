import { DatePipe } from '@angular/common';
import { Component, computed, inject, input, linkedSignal } from '@angular/core';
import { rxResource } from '@angular/core/rxjs-interop';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { HasPermissionDirective } from '@shop/shared';
import { STAFF_PAGE_SIZE, StaffApi, StaffQuery } from './staff.api';

@Component({
  selector: 'adm-staff-list',
  imports: [FormsModule, RouterLink, DatePipe, HasPermissionDirective],
  template: `
    <div class="page-head">
      <h1>Staff</h1>
      <a *shrHasPermission="'users.manage'" class="btn" routerLink="/staff/new">Add staff member</a>
    </div>

    <form class="filters" (ngSubmit)="apply()">
      <label class="visually-hidden" for="q">Search</label>
      <input id="q" name="q" type="search" placeholder="Name or email" [(ngModel)]="search" />
      <label class="visually-hidden" for="role">Role</label>
      <select
        id="role"
        name="role"
        [ngModel]="query().role_id"
        (ngModelChange)="set({ role_id: $event })"
      >
        <option value="">All roles</option>
        @for (r of roles.value() ?? []; track r.id) {
          <option [value]="r.id">{{ r.name }}</option>
        }
      </select>
      <label class="visually-hidden" for="status">Status</label>
      <select
        id="status"
        name="status"
        [ngModel]="query().status"
        (ngModelChange)="set({ status: $event })"
      >
        <option value="">Active and deactivated</option>
        <option value="active">Active only</option>
        <option value="inactive">Deactivated only</option>
      </select>
      <button class="btn btn-secondary" type="submit">Search</button>
    </form>

    @if (staff.error()) {
      <div class="alert-error" role="alert">
        Couldn't load staff.
        <button class="btn btn-secondary" type="button" (click)="staff.reload()">Retry</button>
      </div>
    } @else {
      <div class="card table-wrap">
        <table>
          <thead>
            <tr>
              <th scope="col">Name</th>
              <th scope="col">Roles</th>
              <th scope="col">Status</th>
              <th scope="col">Two-step</th>
              <th scope="col">Last sign-in</th>
            </tr>
          </thead>
          <tbody>
            @for (s of staff.value()?.items ?? []; track s.id) {
              <tr>
                <td>
                  <a [routerLink]="['/staff', s.id]">{{ s.full_name }}</a><br />
                  <small class="muted">{{ s.email }}</small>
                </td>
                <td>{{ s.roles.join(', ') || 'No role' }}</td>
                <td>
                  <span class="state" [class.off]="!s.is_active">{{
                    s.is_active ? 'Active' : 'Deactivated'
                  }}</span>
                </td>
                <td>{{ s.mfa_enabled ? 'On' : 'Not set up' }}</td>
                <td class="nowrap">
                  {{ s.last_login_at ? (s.last_login_at | date: 'dd MMM yyyy, HH:mm') : 'Never' }}
                </td>
              </tr>
            } @empty {
              <tr>
                <td colspan="5" class="empty">
                  {{ staff.isLoading() ? 'Loading…' : 'No staff match.' }}
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
            [disabled]="query().page <= 1"
            (click)="set({ page: query().page - 1 }, false)"
          >
            Previous
          </button>
          <span>Page {{ query().page }} of {{ pages() }}</span>
          <button
            class="btn btn-secondary"
            type="button"
            [disabled]="query().page >= pages()"
            (click)="set({ page: query().page + 1 }, false)"
          >
            Next
          </button>
        </nav>
      }
    }
  `,
  styleUrl: '../products/admin-table.scss',
  styles: `
    .muted {
      color: var(--color-muted);
    }
    .state {
      font-size: var(--font-size-sm);
      font-weight: 600;
      color: var(--color-success);
    }
    .state.off {
      color: var(--color-muted);
    }
  `,
})
export class StaffList {
  private readonly api = inject(StaffApi);

  /** ?role=<id>, used by the staff counts on the Roles page. */
  readonly role = input<string>();

  protected search = '';
  protected readonly query = linkedSignal<StaffQuery>(() => ({
    q: '',
    role_id: this.role() ?? '',
    status: '',
    page: 1,
  }));
  protected readonly roles = rxResource({ stream: () => this.api.roles() });
  protected readonly staff = rxResource({
    params: () => this.query(),
    stream: ({ params }) => this.api.list(params),
  });
  protected readonly pages = computed(() =>
    Math.ceil((this.staff.value()?.total ?? 0) / STAFF_PAGE_SIZE),
  );

  protected set(change: Partial<StaffQuery>, resetPage = true): void {
    this.query.update((q) => ({ ...q, ...change, ...(resetPage ? { page: 1 } : {}) }));
  }

  protected apply(): void {
    this.set({ q: this.search.trim() });
  }
}
