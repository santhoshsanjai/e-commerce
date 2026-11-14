import { signal } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { AuthService } from '@shop/shared';
import { Shell } from './layout/shell';

describe('Admin Shell', () => {
  function setup(permissions: string[]) {
    const granted = signal(new Set(permissions));
    TestBed.configureTestingModule({
      imports: [Shell],
      providers: [
        provideRouter([]),
        {
          provide: AuthService,
          useValue: {
            permissions: granted,
            user: signal({ full_name: 'Mia', roles: ['Manager'] }),
            logout: async () => undefined,
          },
        },
      ],
    });
    return TestBed.createComponent(Shell);
  }

  it('shows menu items the user has permission for', async () => {
    const fixture = setup(['dashboard.view']);
    await fixture.whenStable();
    expect((fixture.nativeElement as HTMLElement).querySelector('nav')?.textContent).toContain(
      'Dashboard',
    );
  });

  it('hides menu items without permission', async () => {
    const fixture = setup([]);
    await fixture.whenStable();
    expect((fixture.nativeElement as HTMLElement).querySelector('nav')?.textContent).not.toContain(
      'Dashboard',
    );
  });
});
