import { Component, signal } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { AuthService } from './auth.service';
import { HasPermissionDirective } from './has-permission.directive';

@Component({
  imports: [HasPermissionDirective],
  template: `<span *shrHasPermission="'orders.export'" id="export">Export</span>
    <span *shrHasPermission="['orders.view', 'users.manage']" id="both">Both</span>`,
})
class Host {}

describe('HasPermissionDirective', () => {
  const granted = signal<string[]>([]);

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [
        {
          provide: AuthService,
          useValue: {
            hasPermission: (...keys: string[]) => keys.every((k) => granted().includes(k)),
          },
        },
      ],
    });
  });

  it('shows and hides content as permissions change', async () => {
    const fixture = TestBed.createComponent(Host);
    await fixture.whenStable();
    const el = fixture.nativeElement as HTMLElement;
    expect(el.querySelector('#export')).toBeNull();

    granted.set(['orders.export', 'orders.view']);
    await fixture.whenStable();
    expect(el.querySelector('#export')).not.toBeNull();
    expect(el.querySelector('#both')).toBeNull();

    granted.set([]);
    await fixture.whenStable();
    expect(el.querySelector('#export')).toBeNull();
  });
});
