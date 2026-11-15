import { TestBed } from '@angular/core/testing';
import { provideRouter, Router } from '@angular/router';
import { AuthService } from '@shop/shared';
import { Login } from './login';

async function setup(auth: Partial<Record<keyof AuthService, unknown>>) {
  TestBed.configureTestingModule({
    imports: [Login],
    providers: [provideRouter([]), { provide: AuthService, useValue: auth }],
  });
  const router = TestBed.inject(Router);
  const navigate = vi.spyOn(router, 'navigateByUrl').mockResolvedValue(true);
  const fixture = TestBed.createComponent(Login);
  await fixture.whenStable();
  const el = fixture.nativeElement as HTMLElement;
  const type = async (id: string, value: string) => {
    const input = el.querySelector(`#${id}`) as HTMLInputElement;
    input.value = value;
    input.dispatchEvent(new Event('input'));
    await fixture.whenStable();
  };
  const click = async (text: string) => {
    const button = [...el.querySelectorAll('button')].find((b) =>
      b.textContent?.trim().startsWith(text),
    );
    button!.click();
    await fixture.whenStable();
  };
  const signIn = async () => {
    await type('email', 'ops@example.com');
    await type('password', 'staff-password-1');
    await click('Sign in');
  };
  return { el, type, click, signIn, navigate };
}

describe('Admin Login', () => {
  it('asks for the app code after the password', async () => {
    const auth = {
      staffLogin: vi.fn(async () => ({ kind: 'verify', challenge: 'ch1' })),
      mfaVerify: vi.fn(async () => ({})),
    };
    const { el, type, click, signIn, navigate } = await setup(auth);
    await signIn();
    expect(el.querySelector('h1')?.textContent).toContain('Two-step sign-in');
    await type('mfa_code', '123456');
    await click('Continue');
    expect(auth.mfaVerify).toHaveBeenCalledWith('ch1', '123456');
    expect(navigate).toHaveBeenCalledWith('/');
  });

  it('accepts a recovery code instead', async () => {
    const auth = {
      staffLogin: vi.fn(async () => ({ kind: 'verify', challenge: 'ch1' })),
      mfaVerify: vi.fn(async () => ({})),
    };
    const { el, type, click, signIn } = await setup(auth);
    await signIn();
    await click('Lost your phone?');
    expect(el.querySelector('label[for=mfa_code]')?.textContent).toContain('Recovery code');
    await type('mfa_code', 'abcd-efgh-jkmn');
    await click('Continue');
    expect(auth.mfaVerify).toHaveBeenCalledWith('ch1', 'abcd-efgh-jkmn');
  });

  it('walks a new staff member through setting up the app', async () => {
    const auth = {
      staffLogin: vi.fn(async () => ({ kind: 'enrol', challenge: 'ch2' })),
      mfaSetup: vi.fn(async () => ({
        secret: 'JBSWY3DPEHPK3PXP',
        otpauth_uri: 'otpauth://totp/x',
        qr_png: 'data:image/png;base64,AAAA',
      })),
      mfaActivate: vi.fn(async () => ['aaaa-bbbb-cccc', 'dddd-eeee-ffff']),
    };
    const { el, type, click, signIn, navigate } = await setup(auth);
    await signIn();
    expect(auth.mfaSetup).toHaveBeenCalledWith('ch2');
    expect((el.querySelector('img.qr') as HTMLImageElement).src).toContain('data:image/png');
    expect(el.querySelector('[data-testid=mfa-secret]')?.textContent).toBe('JBSW Y3DP EHPK 3PXP');

    await type('mfa_code', '12345');
    await click('Turn on');
    expect(el.querySelector('[role=alert]')?.textContent).toContain('6-digit');
    expect(auth.mfaActivate).not.toHaveBeenCalled();

    await type('mfa_code', '123456');
    await click('Turn on');
    expect(auth.mfaActivate).toHaveBeenCalledWith('ch2', '123456');
    expect(el.querySelector('[data-testid=recovery-codes]')?.textContent).toContain(
      'dddd-eeee-ffff',
    );
    expect(navigate).not.toHaveBeenCalled();
    await click("I've saved them");
    expect(navigate).toHaveBeenCalledWith('/');
  });

  it('goes back to the password when the sign-in times out', async () => {
    const auth = {
      staffLogin: vi.fn(async () => ({ kind: 'verify', challenge: 'ch1' })),
      mfaVerify: vi.fn(async () => {
        throw {
          status: 401,
          error: { error: { code: 'mfa_challenge_invalid', message: 'Your sign-in timed out.' } },
        };
      }),
    };
    const { el, type, click, signIn } = await setup(auth);
    await signIn();
    await type('mfa_code', '123456');
    await click('Continue');
    expect(el.querySelector('h1')?.textContent).toContain('Admin sign in');
  });
});
