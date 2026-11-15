import { Component, inject, input, signal } from '@angular/core';
import { NonNullableFormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { Router } from '@angular/router';
import { apiErrorMessage, AuthService, safeReturnUrl } from '@shop/shared';

@Component({
  selector: 'adm-login',
  imports: [ReactiveFormsModule],
  template: `
    <main class="wrap">
      <div class="card">
        <h1>Admin sign in</h1>
        @if (error()) {
          <div class="alert-error" role="alert">{{ error() }}</div>
        }
        <form [formGroup]="form" (ngSubmit)="submit()" novalidate>
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
      </div>
    </main>
  `,
  styles: `
    .wrap {
      max-width: 400px;
      margin: 10vh auto;
      padding: 0 var(--space-4);
    }
    h1 {
      font-size: var(--font-size-xl);
      margin-top: 0;
    }
    .btn {
      width: 100%;
    }
  `,
})
export class Login {
  private readonly auth = inject(AuthService);
  private readonly router = inject(Router);

  /** Bound from the query string; undefined when absent (router input binding). */
  readonly returnUrl = input<string>();

  protected readonly busy = signal(false);
  protected readonly error = signal<string | null>(null);
  protected readonly form = inject(NonNullableFormBuilder).group({
    email: ['', [Validators.required, Validators.email]],
    password: ['', Validators.required],
  });

  async submit(): Promise<void> {
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      this.error.set('Enter your email and password.');
      return;
    }
    this.busy.set(true);
    this.error.set(null);
    try {
      await this.auth.login(this.form.getRawValue(), 'staff');
      await this.router.navigateByUrl(safeReturnUrl(this.returnUrl()));
    } catch (err) {
      this.error.set(apiErrorMessage(err));
    } finally {
      this.busy.set(false);
    }
  }
}
