import { Component, inject, signal } from '@angular/core';
import { NonNullableFormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { apiErrorMessage, AuthService } from '@shop/shared';

@Component({
  selector: 'buy-register',
  imports: [ReactiveFormsModule, RouterLink],
  template: `
    <div class="card">
      <h1>Create account</h1>
      @if (error()) {
        <div class="alert-error" role="alert">{{ error() }}</div>
      }
      <form [formGroup]="form" (ngSubmit)="submit()" novalidate>
        <div class="field">
          <label for="full_name">Full name</label>
          <input id="full_name" formControlName="full_name" autocomplete="name" />
        </div>
        <div class="field">
          <label for="email">Email</label>
          <input id="email" type="email" formControlName="email" autocomplete="email" />
        </div>
        <div class="field">
          <label for="phone">Mobile (optional)</label>
          <input id="phone" type="tel" formControlName="phone" autocomplete="tel" />
        </div>
        <div class="field">
          <label for="password">Password</label>
          <input
            id="password"
            type="password"
            formControlName="password"
            autocomplete="new-password"
            aria-describedby="pw-hint"
          />
          <small id="pw-hint">At least 10 characters.</small>
        </div>
        <button class="btn" type="submit" [disabled]="busy()">
          {{ busy() ? 'Creating account…' : 'Create account' }}
        </button>
      </form>
      <p class="switch">Already have an account? <a routerLink="/login">Sign in</a></p>
    </div>
  `,
  styleUrl: './auth-page.scss',
})
export class Register {
  private readonly auth = inject(AuthService);
  private readonly router = inject(Router);

  protected readonly busy = signal(false);
  protected readonly error = signal<string | null>(null);
  protected readonly form = inject(NonNullableFormBuilder).group({
    full_name: ['', Validators.required],
    email: ['', [Validators.required, Validators.email]],
    phone: [''],
    password: ['', [Validators.required, Validators.minLength(10)]],
  });

  async submit(): Promise<void> {
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      this.error.set('Fill in your name, a valid email and a password of at least 10 characters.');
      return;
    }
    this.busy.set(true);
    this.error.set(null);
    const { phone, ...rest } = this.form.getRawValue();
    try {
      await this.auth.register({ ...rest, phone: phone || null });
      await this.auth.login({ email: rest.email, password: rest.password }, 'buyer');
      await this.router.navigateByUrl('/');
    } catch (err) {
      this.error.set(apiErrorMessage(err));
    } finally {
      this.busy.set(false);
    }
  }
}
