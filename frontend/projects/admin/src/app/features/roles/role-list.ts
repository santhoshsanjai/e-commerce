import { Component, inject } from '@angular/core';
import { rxResource } from '@angular/core/rxjs-interop';
import { RouterLink } from '@angular/router';
import { HasPermissionDirective } from '@shop/shared';
import { StaffApi } from '../staff/staff.api';

@Component({
  selector: 'adm-role-list',
  imports: [RouterLink, HasPermissionDirective],
  template: `
    <div class="page-head">
      <h1>Roles</h1>
      <a *shrHasPermission="'roles.manage'" class="btn" routerLink="/roles/new">New role</a>
    </div>
    <p class="muted intro">
      A role is a set of permissions. Staff can hold more than one role and get every permission
      from all of them.
    </p>

    @if (roles.error()) {
      <div class="alert-error" role="alert">
        Couldn't load roles.
        <button class="btn btn-secondary" type="button" (click)="roles.reload()">Retry</button>
      </div>
    } @else {
      <div class="card table-wrap">
        <table>
          <thead>
            <tr>
              <th scope="col">Role</th>
              <th scope="col" class="num">Permissions</th>
              <th scope="col" class="num">Staff</th>
            </tr>
          </thead>
          <tbody>
            @for (r of roles.value() ?? []; track r.id) {
              <tr>
                <td>
                  <a [routerLink]="['/roles', r.id]">{{ r.name }}</a>
                  @if (r.is_system) {
                    <span class="tag">Built-in</span>
                  }
                  @if (r.description) {
                    <br /><small class="muted">{{ r.description }}</small>
                  }
                </td>
                <td class="num">{{ r.permissions.length }}</td>
                <td class="num">
                  @if (r.user_count) {
                    <a [routerLink]="['/staff']" [queryParams]="{ role: r.id }">{{
                      r.user_count
                    }}</a>
                  } @else {
                    0
                  }
                </td>
              </tr>
            } @empty {
              <tr>
                <td colspan="3" class="empty">
                  {{ roles.isLoading() ? 'Loading…' : 'No roles.' }}
                </td>
              </tr>
            }
          </tbody>
        </table>
      </div>
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
    .tag {
      margin-left: var(--space-2);
      font-size: var(--font-size-sm);
      color: var(--color-muted);
      border: 1px solid var(--color-border);
      border-radius: var(--radius-sm);
      padding: 0 var(--space-1);
    }
  `,
})
export class RoleList {
  private readonly api = inject(StaffApi);
  protected readonly roles = rxResource({ stream: () => this.api.roles() });
}
