import { Component, inject, input, signal } from '@angular/core';
import {
  FormsModule,
  NonNullableFormBuilder,
  ReactiveFormsModule,
  Validators,
} from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { apiErrorMessage, AuthService, MfaSetup, safeReturnUrl } from '@shop/shared';

type Step = 'password' | 'verify' | 'enrol' | 'recovery-codes';

/**
 * Staff sign-in: password, then a code from the authenticator app. The first time, staff set up
 * the app (scan a QR code, confirm a code) and are shown recovery codes once.
 */
@Component({
  selector: 'adm-login',
  imports: [ReactiveFormsModule, FormsModule, RouterLink],
  template: `
    <main class="wrap">
      <div class="card">
        @switch (step()) {
          @case ('password') {
            <h1>Admin sign in</h1>
            @if (error()) {
              <div class="alert-error" role="alert">{{ error() }}</div>
            }
            <form [formGroup]="form" (ngSubmit)="submitPassword()" novalidate>
              <div class="field">
                <label for="email">Email</label>
                <input id="email" type="email" formControlName="email" autocomplete="username" />
              </div>
              <div class="field">
                <label for="password">Password</label>
                <input
                  id="password"
                  type="password"
                  formControlName="password"
                  autocomplete="current-password"
                />
              </div>
              <button class="btn" type="submit" [disabled]="busy()">
                {{ busy() ? 'Signing in…' : 'Sign in' }}
              </button>
            </form>
            <p class="foot"><a routerLink="/forgot-password">Forgot your password?</a></p>
          }
          @case ('verify') {
            <h1>Two-step sign-in</h1>
            @if (useRecovery()) {
              <p>Enter one of the recovery codes you saved when you set up two-step sign-in.</p>
            } @else {
              <p>Open your authenticator app and enter the 6-digit code for this account.</p>
            }
            @if (error()) {
              <div class="alert-error" role="alert">{{ error() }}</div>
            }
            <form (ngSubmit)="submitCode()" novalidate>
              <div class="field">
                @if (useRecovery()) {
                  <label for="mfa_code">Recovery code</label>
                  <input
                    id="mfa_code"
                    name="code"
                    autocomplete="off"
                    spellcheck="false"
                    [(ngModel)]="code"
                  />
                } @else {
                  <label for="mfa_code">Code</label>
                  <input
                    id="mfa_code"
                    name="code"
                    inputmode="numeric"
                    autocomplete="one-time-code"
                    maxlength="6"
                    [(ngModel)]="code"
                  />
                }
              </div>
              <button class="btn" type="submit" [disabled]="busy()">
                {{ busy() ? 'Checking…' : 'Continue' }}
              </button>
            </form>
            <p class="foot">
              <button class="link" type="button" (click)="toggleRecovery()">
                {{
                  useRecovery() ? 'Use a code from the app' : 'Lost your phone? Use a recovery code'
                }}
              </button>
            </p>
            <p class="foot">
              <button class="link" type="button" (click)="restart()">Start again</button>
            </p>
          }
          @case ('enrol') {
            <h1>Set up two-step sign-in</h1>
            <p>
              Staff accounts need a code from an authenticator app (such as Google Authenticator,
              Microsoft Authenticator or 1Password) as well as the password.
            </p>
            @if (error()) {
              <div class="alert-error" role="alert">{{ error() }}</div>
            }
            @if (setup(); as s) {
              <ol class="steps">
                <li>
                  Scan this QR code with the app.
                  <img class="qr" [src]="s.qr_png" alt="QR code to add this account to your app" />
                  <details>
                    <summary>Can't scan it?</summary>
                    <p>Add an account by hand and type in this key:</p>
                    <code class="secret" data-testid="mfa-secret">{{ grouped(s.secret) }}</code>
                  </details>
                </li>
                <li>
                  Enter the 6-digit code the app shows.
                  <form (ngSubmit)="submitActivation()" novalidate>
                    <div class="field">
                      <label for="mfa_code">Code</label>
                      <input
                        id="mfa_code"
                        name="code"
                        inputmode="numeric"
                        autocomplete="one-time-code"
                        maxlength="6"
                        [(ngModel)]="code"
                      />
                    </div>
                    <button class="btn" type="submit" [disabled]="busy()">
                      {{ busy() ? 'Checking…' : 'Turn on two-step sign-in' }}
                    </button>
                  </form>
                </li>
              </ol>
            } @else if (!error()) {
              <p aria-busy="true">Preparing…</p>
            }
            <p class="foot">
              <button class="link" type="button" (click)="restart()">Start again</button>
            </p>
          }
          @case ('recovery-codes') {
            <h1>Save your recovery codes</h1>
            <p>
              If you lose your phone, each of these codes lets you sign in once. Keep them somewhere
              safe, such as a password manager. They won't be shown again.
            </p>
            <ul class="codes" data-testid="recovery-codes">
              @for (c of recoveryCodes(); track c) {
                <li>
                  <code>{{ c }}</code>
                </li>
              }
            </ul>
            <button class="btn btn-secondary" type="button" (click)="copyCodes()">
              {{ copied() ? 'Copied' : 'Copy codes' }}
            </button>
            <button class="btn" type="button" (click)="finish()">I've saved them, continue</button>
          }
        }
      </div>
    </main>
  `,
  styles: `
    :host {
      display: grid;
      place-items: center;
      min-height: 100vh;
      padding: var(--space-8) var(--space-4);
      background:
        radial-gradient(
          circle at 20% 10%,
          color-mix(in srgb, var(--color-accent) 30%, transparent),
          transparent 40%
        ),
        linear-gradient(140deg, var(--color-sidebar-bg), var(--color-hero-end));
    }
    .wrap {
      width: 100%;
      max-width: 440px;
      animation: fade-up var(--duration-slow) var(--ease-out) both;
    }
    .wrap > .card {
      padding: var(--space-10) var(--space-8);
      box-shadow: var(--shadow-lg);
    }
    h1 {
      font-size: var(--font-size-2xl);
      margin-top: 0;
    }
    .btn {
      width: 100%;
      margin-top: var(--space-2);
    }
    .foot {
      text-align: center;
      margin: var(--space-4) 0 0;
    }
    .link {
      background: none;
      border: 0;
      padding: 0;
      color: var(--color-primary);
      text-decoration: underline;
      cursor: pointer;
      font: inherit;
    }
    .steps {
      padding-left: var(--space-6);
    }
    .steps li + li {
      margin-top: var(--space-4);
    }
    .qr {
      display: block;
      width: 200px;
      height: 200px;
      margin: var(--space-3) 0;
      background: #fff; /* scanners need a white quiet zone, whatever the theme */
    }
    .secret {
      display: block;
      word-break: break-all;
      font-size: var(--font-size-md);
      letter-spacing: 0.05em;
    }
    .codes {
      list-style: none;
      padding: 0;
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: var(--space-2);
    }
  `,
})
export class Login {
  private readonly auth = inject(AuthService);
  private readonly router = inject(Router);

  /** Bound from the query string; undefined when absent (router input binding). */
  readonly returnUrl = input<string>();

  protected readonly step = signal<Step>('password');
  protected readonly busy = signal(false);
  protected readonly error = signal<string | null>(null);
  protected readonly setup = signal<MfaSetup | null>(null);
  protected readonly useRecovery = signal(false);
  protected readonly recoveryCodes = signal<string[]>([]);
  protected readonly copied = signal(false);
  protected code = '';
  private challenge = '';

  protected readonly form = inject(NonNullableFormBuilder).group({
    email: ['', [Validators.required, Validators.email]],
    password: ['', Validators.required],
  });

  async submitPassword(): Promise<void> {
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      this.error.set('Enter your email and password.');
      return;
    }
    await this.run(async () => {
      const next = await this.auth.staffLogin(this.form.getRawValue());
      if (next.kind === 'signed-in') {
        await this.finish();
        return;
      }
      this.challenge = next.challenge;
      this.form.controls.password.reset();
      this.code = '';
      this.step.set(next.kind);
      if (next.kind === 'enrol') {
        this.setup.set(await this.auth.mfaSetup(this.challenge));
      }
    });
  }

  async submitCode(): Promise<void> {
    if (!this.code.trim()) {
      this.error.set(this.useRecovery() ? 'Enter a recovery code.' : 'Enter the 6-digit code.');
      return;
    }
    await this.run(async () => {
      await this.auth.mfaVerify(this.challenge, this.code.trim());
      await this.finish();
    });
  }

  async submitActivation(): Promise<void> {
    if (!/^\d{6}$/.test(this.code.trim())) {
      this.error.set('Enter the 6-digit code from the app.');
      return;
    }
    await this.run(async () => {
      this.recoveryCodes.set(await this.auth.mfaActivate(this.challenge, this.code.trim()));
      this.setup.set(null);
      this.step.set('recovery-codes');
    });
  }

  protected toggleRecovery(): void {
    this.useRecovery.update((v) => !v);
    this.code = '';
    this.error.set(null);
  }

  protected restart(): void {
    this.step.set('password');
    this.setup.set(null);
    this.useRecovery.set(false);
    this.code = '';
    this.challenge = '';
    this.error.set(null);
  }

  protected grouped(secret: string): string {
    return secret.replace(/(.{4})/g, '$1 ').trim();
  }

  protected async copyCodes(): Promise<void> {
    try {
      await navigator.clipboard.writeText(this.recoveryCodes().join('\n'));
      this.copied.set(true);
    } catch {
      this.error.set("Couldn't copy. Select the codes and copy them yourself.");
    }
  }

  protected async finish(): Promise<void> {
    this.recoveryCodes.set([]);
    await this.router.navigateByUrl(safeReturnUrl(this.returnUrl()));
  }

  private async run(action: () => Promise<void>): Promise<void> {
    this.busy.set(true);
    this.error.set(null);
    try {
      await action();
    } catch (err) {
      this.error.set(apiErrorMessage(err));
      // A timed-out challenge can't be fixed here: go back to the password.
      if (
        (err as { error?: { error?: { code?: string } } })?.error?.error?.code ===
        'mfa_challenge_invalid'
      ) {
        this.restart();
        this.error.set(apiErrorMessage(err));
      }
    } finally {
      this.busy.set(false);
    }
  }
}
