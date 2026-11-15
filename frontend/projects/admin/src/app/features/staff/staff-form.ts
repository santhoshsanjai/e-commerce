import { DatePipe } from '@angular/common';
import { Component, computed, inject, input, linkedSignal, signal } from '@angular/core';
import { rxResource } from '@angular/core/rxjs-interop';
import { FormsModule } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { apiErrorMessage, AuthService } from '@shop/shared';
import { of } from 'rxjs';
import { Role, StaffApi, StaffMember, SUPER_ADMIN } from './staff.api';

const MIN_PASSWORD = 12;

@Component({
  selector: 'adm-staff-form',
  imports: [FormsModule, RouterLink, DatePipe],
  templateUrl: './staff-form.html',
  styleUrl: './staff-form.scss',
})
export class StaffForm {
  private readonly api = inject(StaffApi);
  private readonly auth = inject(AuthService);
  private readonly router = inject(Router);

  /** Route parameter; absent on /staff/new. */
  readonly id = input<string>();
  /** Set by the redirect after adding someone, so the confirmation survives the navigation. */
  readonly created = input<string>();

  protected readonly minPassword = MIN_PASSWORD;
  protected readonly isNew = computed(() => !this.id());
  protected readonly member = rxResource({
    params: () => this.id(),
    stream: ({ params }) => (params ? this.api.get(params) : of(null)),
  });
  protected readonly roles = rxResource({ stream: () => this.api.roles() });

  protected readonly fullName = linkedSignal(() => this.member.value()?.full_name ?? '');
  protected readonly phone = linkedSignal(() => this.member.value()?.phone ?? '');
  protected readonly roleIds = linkedSignal(() => this.member.value()?.role_ids ?? []);
  protected email = '';
  protected password = '';
  protected newPassword = '';

  protected readonly error = signal<string | null>(null);
  protected readonly notice = linkedSignal<string | null>(() =>
    this.created() ? 'Staff member added. Share their password with them privately.' : null,
  );
  protected readonly busy = signal(false);
  protected readonly confirmingDeactivate = signal(false);
  protected readonly confirmingMfaReset = signal(false);

  private readonly iAmSuperAdmin = computed(
    () => this.auth.user()?.roles.includes(SUPER_ADMIN) ?? false,
  );
  protected readonly canManage = computed(() => this.auth.hasPermission('users.manage'));
  protected readonly isSelf = computed(() => this.member.value()?.id === this.auth.user()?.id);
  /** Admins can see a Super Admin's account but only another Super Admin can change it. */
  protected readonly lockedSuperAdmin = computed(
    () => (this.member.value()?.roles.includes(SUPER_ADMIN) ?? false) && !this.iAmSuperAdmin(),
  );
  protected readonly editable = computed(() => this.canManage() && !this.lockedSuperAdmin());

  protected roleDisabled(role: Role): boolean {
    if (!this.editable() || this.isSelf()) return true;
    return role.name === SUPER_ADMIN && !this.iAmSuperAdmin();
  }

  protected toggleRole(role: Role, checked: boolean): void {
    this.roleIds.update((ids) => (checked ? [...ids, role.id] : ids.filter((i) => i !== role.id)));
  }

  protected canSubmit(): boolean {
    if (!this.editable() || this.busy() || !this.fullName().trim() || !this.roleIds().length) {
      return false;
    }
    return !this.isNew() || (!!this.email.trim() && this.password.length >= MIN_PASSWORD);
  }

  protected async save(): Promise<void> {
    await this.run(async () => {
      const phone = this.phone().trim() || null;
      if (this.isNew()) {
        const created = await this.api.create({
          email: this.email.trim(),
          full_name: this.fullName().trim(),
          phone,
          password: this.password,
          role_ids: this.roleIds(),
        });
        await this.router.navigate(['/staff', created.id], { queryParams: { created: 1 } });
        return null;
      }
      const member = this.member.value() as StaffMember;
      const updated = await this.api.update(member.id, {
        full_name: this.fullName().trim(),
        phone,
        ...(this.isSelf() ? {} : { role_ids: this.roleIds() }),
      });
      this.member.set(updated);
      return 'Changes saved.';
    });
  }

  protected async setActive(active: boolean): Promise<void> {
    this.confirmingDeactivate.set(false);
    await this.run(async () => {
      const member = this.member.value() as StaffMember;
      this.member.set(await this.api.update(member.id, { is_active: active }));
      return active
        ? `${member.full_name} can sign in again.`
        : `${member.full_name} is deactivated and has been signed out everywhere.`;
    });
  }

  protected async resetPassword(): Promise<void> {
    await this.run(async () => {
      const member = this.member.value() as StaffMember;
      await this.api.resetPassword(member.id, this.newPassword);
      this.newPassword = '';
      return `Password changed. ${member.full_name} has been signed out and must use the new password.`;
    });
  }

  protected async resetMfa(): Promise<void> {
    this.confirmingMfaReset.set(false);
    await this.run(async () => {
      const member = this.member.value() as StaffMember;
      await this.api.resetMfa(member.id);
      this.member.set({ ...member, mfa_enabled: false });
      return `Two-step sign-in reset. ${member.full_name} has been signed out and will set up their authenticator app again at their next sign-in.`;
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
    }
  }
}
