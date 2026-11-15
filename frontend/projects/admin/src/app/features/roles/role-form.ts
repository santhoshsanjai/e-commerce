import { Component, computed, inject, input, linkedSignal, signal } from '@angular/core';
import { rxResource } from '@angular/core/rxjs-interop';
import { FormsModule } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { apiErrorMessage, AuthService } from '@shop/shared';
import { map } from 'rxjs';
import { Role, StaffApi, SUPER_ADMIN } from '../staff/staff.api';
import { groupPermissions } from './permission-groups';

@Component({
  selector: 'adm-role-form',
  imports: [FormsModule, RouterLink],
  templateUrl: './role-form.html',
  styleUrl: './role-form.scss',
})
export class RoleForm {
  private readonly api = inject(StaffApi);
  private readonly auth = inject(AuthService);
  private readonly router = inject(Router);

  /** Route parameter; absent on /roles/new. */
  readonly id = input<string>();
  /** Set by the redirect after creating a role, so the confirmation survives the navigation. */
  readonly created = input<string>();

  protected readonly isNew = computed(() => !this.id());
  private readonly roles = rxResource({ stream: () => this.api.roles() });
  protected readonly groups = rxResource({
    stream: () => this.api.permissions().pipe(map(groupPermissions)),
  });
  protected readonly role = computed<Role | null>(
    () => this.roles.value()?.find((r) => r.id === this.id()) ?? null,
  );
  protected readonly notFound = computed(
    () => !this.isNew() && !!this.roles.value() && !this.role(),
  );

  protected readonly name = linkedSignal(() => this.role()?.name ?? '');
  protected readonly description = linkedSignal(() => this.role()?.description ?? '');
  protected readonly selected = linkedSignal(() => new Set(this.role()?.permissions ?? []));

  protected readonly error = signal<string | null>(null);
  protected readonly notice = linkedSignal<string | null>(() =>
    this.created() ? 'Role created. Give it to staff from the Staff page.' : null,
  );
  protected readonly busy = signal(false);
  protected readonly confirmingDelete = signal(false);

  protected readonly isSuperAdminRole = computed(() => this.role()?.name === SUPER_ADMIN);
  protected readonly editable = computed(
    () => this.auth.hasPermission('roles.manage') && !this.isSuperAdminRole(),
  );

  /** You can remove any permission, but only add ones you hold yourself (the API checks too). */
  protected permissionDisabled(key: string): boolean {
    if (!this.editable()) return true;
    return !this.auth.hasPermission(key) && !this.selected().has(key);
  }

  protected toggle(key: string, checked: boolean): void {
    this.selected.update((current) => {
      const next = new Set(current);
      if (checked) next.add(key);
      else next.delete(key);
      return next;
    });
  }

  protected async save(): Promise<void> {
    await this.run(async () => {
      const body = {
        description: this.description().trim(),
        permissions: [...this.selected()].sort(),
        ...(this.role()?.is_system ? {} : { name: this.name().trim() }),
      };
      const current = this.role();
      if (!current) {
        const created = await this.api.createRole(body);
        await this.router.navigate(['/roles', created.id], { queryParams: { created: 1 } });
        return null;
      }
      await this.api.updateRole(current.id, body);
      this.roles.reload();
      return 'Changes saved. Staff with this role get the new permissions straight away.';
    });
  }

  protected async remove(): Promise<void> {
    const current = this.role();
    if (!current) return;
    await this.run(async () => {
      await this.api.deleteRole(current.id);
      await this.router.navigate(['/roles']);
      return null;
    });
  }

  private async run(action: () => Promise<string | null>): Promise<void> {
    this.error.set(null);
    this.notice.set(null);
    this.busy.set(true);
    try {
      const message = await action();
      if (message) this.notice.set(message);
    } catch (err) {
      this.error.set(apiErrorMessage(err));
    } finally {
      this.busy.set(false);
      this.confirmingDelete.set(false);
    }
  }
}
