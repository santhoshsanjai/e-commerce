import { Location } from '@angular/common';
import { Component, inject, input, OnInit, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { apiErrorMessage } from '../api/api-error';
import { AuthService } from './auth.service';

const PAGE_STYLES = `
  :host {
    display: block;
    max-width: 420px;
    margin: var(--space-8) auto;
    padding: 0 var(--space-4);
  }
  h1 {
    font-size: var(--font-size-xl);
    margin-top: 0;
  }
  .btn {
    width: 100%;
  }
  .switch {
    text-align: center;
    margin-top: var(--space-4);
    color: var(--color-muted);
  }
  .notice {
    padding: var(--space-3);
    border-radius: var(--radius-md);
    background: color-mix(in srgb, var(--color-success) 10%, transparent);
    color: var(--color-success);
    margin-bottom: var(--space-4);
  }
`;

/** "Forgot your password?" page, shared by the buyer and admin apps. */
@Component({
  selector: 'shr-forgot-password',
  imports: [FormsModule, RouterLink],
  template: `
    <div class="card">
      <h1>Reset your password</h1>
      @if (sent(); as message) {
        <div class="notice" role="status">{{ message }}</div>
        <p>
          The link works for 30 minutes. Check your spam folder if it doesn't arrive in a few
          minutes.
        </p>
      } @else {
        <p>Enter the email you sign in with, and we'll send you a link to choose a new password.</p>
        @if (error()) {
          <div class="alert-error" role="alert">{{ error() }}</div>
        }
        <form (ngSubmit)="submit()" novalidate>
          <div class="field">
            <label for="reset_email">Email</label>
            <input
              id="reset_email"
              name="email"
              type="email"
              autocomplete="email"
              required
              [(ngModel)]="email"
            />
          </div>
          <button class="btn" type="submit" [disabled]="busy()">
            {{ busy() ? 'Sending…' : 'Send reset link' }}
          </button>
        </form>
      }
      <p class="switch"><a [routerLink]="signInPath()">Back to sign in</a></p>
    </div>
  `,
  styles: PAGE_STYLES,
})
export class ForgotPassword {
  private readonly auth = inject(AuthService);

  readonly signInPath = input('/login');

  protected email = '';
  protected readonly busy = signal(false);
  protected readonly error = signal<string | null>(null);
  protected readonly sent = signal<string | null>(null);

  async submit(): Promise<void> {
    if (!/^\S+@\S+\.\S+$/.test(this.email.trim())) {
      this.error.set('Enter the email address you sign in with.');
      return;
    }
    this.busy.set(true);
    this.error.set(null);
    try {
      this.sent.set(await this.auth.requestPasswordReset(this.email.trim()));
    } catch (err) {
      this.error.set(apiErrorMessage(err));
    } finally {
      this.busy.set(false);
    }
  }
}

/** Page the emailed link opens: choose a new password. */
@Component({
  selector: 'shr-reset-password',
  imports: [FormsModule, RouterLink],
  template: `
    <div class="card">
      <h1>Choose a new password</h1>
      @if (done()) {
        <div class="notice" role="status">
          Your password is changed, and you've been signed out on every device.
        </div>
        <a class="btn" [routerLink]="signInPath()">Sign in</a>
      } @else if (!linkToken()) {
        <div class="alert-error" role="alert">
          This link is incomplete. Open the link from the email again, or ask for a new one.
        </div>
        <p class="switch"><a [routerLink]="forgotPath()">Ask for a new link</a></p>
      } @else {
        @if (error()) {
          <div class="alert-error" role="alert">
            {{ error() }}
            @if (linkExpired()) {
              <a [routerLink]="forgotPath()">Ask for a new link</a>
            }
          </div>
        }
        <form (ngSubmit)="submit()" novalidate>
          <div class="field">
            <label for="reset_new_password">New password</label>
            <input
              id="reset_new_password"
              name="new_password"
              type="password"
              autocomplete="new-password"
              aria-describedby="reset_pw_hint"
              [(ngModel)]="newPassword"
            />
            <small id="reset_pw_hint" class="muted">At least {{ minPassword() }} characters.</small>
          </div>
          <div class="field">
            <label for="reset_confirm_password">New password again</label>
            <input
              id="reset_confirm_password"
              name="confirm_password"
              type="password"
              autocomplete="new-password"
              [(ngModel)]="confirmPassword"
            />
          </div>
          <button class="btn" type="submit" [disabled]="busy()">
            {{ busy() ? 'Saving…' : 'Save new password' }}
          </button>
        </form>
      }
    </div>
  `,
  styles: PAGE_STYLES,
})
export class ResetPassword implements OnInit {
  private readonly auth = inject(AuthService);
  private readonly location = inject(Location);

  /** From the link's query string (router input binding). */
  readonly token = input<string>();
  readonly minPassword = input(10);
  readonly signInPath = input('/login');
  readonly forgotPath = input('/forgot-password');

  protected readonly linkToken = signal<string | null>(null);
  protected newPassword = '';
  protected confirmPassword = '';
  protected readonly busy = signal(false);
  protected readonly done = signal(false);
  protected readonly error = signal<string | null>(null);
  protected readonly linkExpired = signal(false);

  ngOnInit(): void {
    this.linkToken.set(this.token() ?? null);
    // Keep the secret out of the address bar and browser history once it's read.
    if (this.token()) {
      this.location.replaceState(this.location.path().split('?')[0]);
    }
  }

  async submit(): Promise<void> {
    const token = this.linkToken();
    if (!token) return;
    if (this.newPassword.length < this.minPassword()) {
      this.error.set(`Your new password needs at least ${this.minPassword()} characters.`);
      return;
    }
    if (this.newPassword !== this.confirmPassword) {
      this.error.set("The two passwords don't match.");
      return;
    }
    this.busy.set(true);
    this.error.set(null);
    this.linkExpired.set(false);
    try {
      await this.auth.resetPassword(token, this.newPassword);
      this.newPassword = this.confirmPassword = '';
      this.done.set(true);
    } catch (err) {
      this.error.set(apiErrorMessage(err));
      this.linkExpired.set(apiErrorCode(err) === 'reset_link_invalid');
    } finally {
      this.busy.set(false);
    }
  }
}

function apiErrorCode(err: unknown): string | undefined {
  const body = (err as { error?: { error?: { code?: string } } } | null)?.error;
  return body?.error?.code;
}
