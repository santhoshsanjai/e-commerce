import { signal } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { AuthService } from '@shop/shared';
import { of } from 'rxjs';
import { Role, StaffApi, StaffMember } from './staff.api';
import { StaffForm } from './staff-form';

const role = (id: string, name: string): Role => ({
  id,
  name,
  description: '',
  is_system: true,
  permissions: [],
  user_count: 1,
});
const roles = [role('r-super', 'Super Admin'), role('r-admin', 'Admin'), role('r-man', 'Manager')];

const member = (over: Partial<StaffMember> = {}): StaffMember => ({
  id: 'u-2',
  email: 'priya@example.com',
  full_name: 'Priya',
  phone: null,
  is_active: true,
  roles: ['Manager'],
  role_ids: ['r-man'],
  last_login_at: null,
  created_at: '2026-11-01T00:00:00Z',
  ...over,
});

async function setup(me: { id: string; roles: string[] }, target: StaffMember) {
  const api = {
    get: vi.fn(() => of(target)),
    roles: vi.fn(() => of(roles)),
    update: vi.fn(async (_id: string, body: object) => ({ ...target, ...body })),
    resetPassword: vi.fn(async () => undefined),
  };
  const auth = {
    user: signal({ ...me, email: 'me@example.com' }),
    hasPermission: () => true,
  };
  TestBed.configureTestingModule({
    imports: [StaffForm],
    providers: [
      provideRouter([]),
      { provide: StaffApi, useValue: api },
      { provide: AuthService, useValue: auth },
    ],
  });
  const fixture = TestBed.createComponent(StaffForm);
  fixture.componentRef.setInput('id', target.id);
  await fixture.whenStable();
  const el = fixture.nativeElement as HTMLElement;
  const box = (name: string) =>
    [...el.querySelectorAll('label.role')]
      .find((l) => l.querySelector('strong')?.textContent?.trim() === name)!
      .querySelector('input') as HTMLInputElement;
  const button = (text: string) =>
    [...el.querySelectorAll('button')].find((b) => b.textContent?.includes(text));
  return { api, fixture, el, box, button };
}

describe('StaffForm', () => {
  it('lets an Admin change roles but not grant Super Admin', async () => {
    const { api, fixture, box, button } = await setup({ id: 'u-1', roles: ['Admin'] }, member());
    expect(box('Super Admin').disabled).toBe(true);
    expect(box('Manager').checked).toBe(true);

    box('Admin').checked = true;
    box('Admin').dispatchEvent(new Event('change'));
    await fixture.whenStable();
    button('Save changes')!.click();
    await fixture.whenStable();
    expect(api.update).toHaveBeenCalledWith('u-2', {
      full_name: 'Priya',
      phone: null,
      role_ids: ['r-man', 'r-admin'],
    });
  });

  it("doesn't let you change your own roles or deactivate yourself", async () => {
    const { el, box, button } = await setup(
      { id: 'u-2', roles: ['Super Admin'] },
      member({ id: 'u-2', roles: ['Super Admin'], role_ids: ['r-super'] }),
    );
    expect(box('Manager').disabled).toBe(true);
    expect(el.textContent).toContain("You can't change your own roles");
    expect(button('Deactivate')).toBeUndefined();
  });

  it("shows a Super Admin's account read-only to an Admin", async () => {
    const { el, button } = await setup(
      { id: 'u-1', roles: ['Admin'] },
      member({ roles: ['Super Admin'], role_ids: ['r-super'] }),
    );
    expect(el.textContent).toContain("Only a Super Admin can change a Super Admin's account");
    expect(button('Save changes')).toBeUndefined();
    expect((el.querySelector('#name') as HTMLInputElement).disabled).toBe(true);
  });

  it('asks before deactivating', async () => {
    const { api, fixture, el, button } = await setup(
      { id: 'u-1', roles: ['Super Admin'] },
      member(),
    );
    button('Deactivate…')!.click();
    await fixture.whenStable();
    expect(api.update).not.toHaveBeenCalled();
    button('Yes, deactivate Priya')!.click();
    await fixture.whenStable();
    expect(api.update).toHaveBeenCalledWith('u-2', { is_active: false });
    expect(el.querySelector('[role=status]')?.textContent).toContain('signed out everywhere');
    expect(button('Reactivate')).toBeDefined();
  });
});
