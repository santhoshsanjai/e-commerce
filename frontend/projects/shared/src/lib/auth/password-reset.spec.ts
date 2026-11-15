import { HttpErrorResponse } from '@angular/common/http';
import { Location } from '@angular/common';
import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { AuthService } from './auth.service';
import { ForgotPassword, ResetPassword } from './password-reset';

function helpers(fixture: { nativeElement: unknown; whenStable(): Promise<unknown> }) {
  const el = fixture.nativeElement as HTMLElement;
  const type = async (id: string, value: string) => {
    const input = el.querySelector(`#${id}`) as HTMLInputElement;
    input.value = value;
    input.dispatchEvent(new Event('input'));
    await fixture.whenStable();
  };
  const submit = async () => {
    (el.querySelector('button[type=submit]') as HTMLButtonElement).click();
    await fixture.whenStable();
  };
  return { el, type, submit };
}

describe('ForgotPassword', () => {
  it('sends the email and shows the same message whatever the answer', async () => {
    const auth = {
      requestPasswordReset: vi.fn(async () => "If an account uses that email, we've sent a link."),
    };
    TestBed.configureTestingModule({
      imports: [ForgotPassword],
      providers: [provideRouter([]), { provide: AuthService, useValue: auth }],
    });
    const fixture = TestBed.createComponent(ForgotPassword);
    await fixture.whenStable();
    const { el, type, submit } = helpers(fixture);

    await submit();
    expect(el.querySelector('[role=alert]')?.textContent).toContain('Enter the email');
    expect(auth.requestPasswordReset).not.toHaveBeenCalled();

    await type('reset_email', ' asha@example.com ');
    await submit();
    expect(auth.requestPasswordReset).toHaveBeenCalledWith('asha@example.com');
    expect(el.querySelector('[role=status]')?.textContent).toContain("we've sent a link");
  });
});

describe('ResetPassword', () => {
  async function setup(token: string | undefined, resetPassword = vi.fn(async () => undefined)) {
    const location = { path: vi.fn(() => '/reset-password?token=abc'), replaceState: vi.fn() };
    TestBed.configureTestingModule({
      imports: [ResetPassword],
      providers: [
        provideRouter([]),
        { provide: AuthService, useValue: { resetPassword } },
        { provide: Location, useValue: location },
      ],
    });
    const fixture = TestBed.createComponent(ResetPassword);
    if (token) fixture.componentRef.setInput('token', token);
    await fixture.whenStable();
    return { fixture, location, resetPassword, ...helpers(fixture) };
  }

  it('takes the token out of the address bar and sets the new password', async () => {
    const { location, resetPassword, el, type, submit } = await setup('abc');
    expect(location.replaceState).toHaveBeenCalledWith('/reset-password');

    await type('reset_new_password', 'new-password-1');
    await type('reset_confirm_password', 'new-password-2');
    await submit();
    expect(el.querySelector('[role=alert]')?.textContent).toContain("don't match");
    expect(resetPassword).not.toHaveBeenCalled();

    await type('reset_confirm_password', 'new-password-1');
    await submit();
    expect(resetPassword).toHaveBeenCalledWith('abc', 'new-password-1');
    expect(el.querySelector('[role=status]')?.textContent).toContain('signed out on every device');
  });

  it('offers a new link when this one has expired', async () => {
    const expired = new HttpErrorResponse({
      status: 400,
      error: { error: { code: 'reset_link_invalid', message: 'This reset link has expired.' } },
    });
    const { el, type, submit } = await setup(
      'abc',
      vi.fn(async () => {
        throw expired;
      }),
    );
    await type('reset_new_password', 'new-password-1');
    await type('reset_confirm_password', 'new-password-1');
    await submit();
    const alert = el.querySelector('[role=alert]')!;
    expect(alert.textContent).toContain('This reset link has expired.');
    expect(alert.querySelector('a')?.textContent).toContain('Ask for a new link');
  });

  it('explains when the link has no token', async () => {
    const { el } = await setup(undefined);
    expect(el.querySelector('[role=alert]')?.textContent).toContain('link is incomplete');
    expect(el.querySelector('form')).toBeNull();
  });
});
