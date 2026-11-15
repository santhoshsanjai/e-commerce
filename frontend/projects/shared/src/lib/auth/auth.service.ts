import { HttpClient } from '@angular/common/http';
import { computed, inject, Injectable, signal } from '@angular/core';
import { firstValueFrom } from 'rxjs';
import { API_BASE_URL } from '../api/api-config';
import {
  Audience,
  LoginRequest,
  Me,
  ProfileUpdate,
  RegisterRequest,
  TokenResponse,
} from '../models/auth.models';

/**
 * Holds the session for one app.
 *
 * The access token lives only in memory; the refresh token is an httpOnly cookie the browser sends
 * to /auth/refresh, so a page reload restores the session without exposing tokens to scripts.
 */
@Injectable({ providedIn: 'root' })
export class AuthService {
  private readonly http = inject(HttpClient);
  private readonly baseUrl = inject(API_BASE_URL);

  private readonly token = signal<string | null>(null);
  private readonly currentUser = signal<Me | null>(null);
  private refreshInFlight: Promise<string | null> | null = null;

  readonly user = this.currentUser.asReadonly();
  readonly isAuthenticated = computed(() => this.currentUser() !== null);
  readonly permissions = computed(() => new Set(this.currentUser()?.permissions ?? []));

  accessToken(): string | null {
    return this.token();
  }

  hasPermission(...keys: string[]): boolean {
    const granted = this.permissions();
    return keys.every((key) => granted.has(key));
  }

  async login(credentials: LoginRequest, audience: Audience): Promise<Me> {
    const path = audience === 'staff' ? '/auth/staff/login' : '/auth/login';
    const res = await firstValueFrom(
      this.http.post<TokenResponse>(`${this.baseUrl}${path}`, credentials, {
        withCredentials: true,
      }),
    );
    this.token.set(res.access_token);
    return this.loadMe();
  }

  async register(data: RegisterRequest): Promise<Me> {
    return firstValueFrom(this.http.post<Me>(`${this.baseUrl}/auth/register`, data));
  }

  /** Change your own name or phone; the signed-in user updates everywhere straight away. */
  async updateProfile(data: ProfileUpdate): Promise<Me> {
    const me = await firstValueFrom(this.http.patch<Me>(`${this.baseUrl}/auth/me`, data));
    this.currentUser.set(me);
    return me;
  }

  /**
   * Change your own password. The API signs out every other device and sends fresh tokens (and a
   * new refresh cookie) for this one, so the person stays signed in here.
   */
  async changePassword(currentPassword: string, newPassword: string): Promise<void> {
    const res = await firstValueFrom(
      this.http.post<TokenResponse>(
        `${this.baseUrl}/auth/change-password`,
        { current_password: currentPassword, new_password: newPassword },
        { withCredentials: true },
      ),
    );
    this.token.set(res.access_token);
  }

  /**
   * Ask for a reset link by email. The API answers the same whether or not the account exists,
   * so this resolves with the message to show either way.
   */
  async requestPasswordReset(email: string): Promise<string> {
    const res = await firstValueFrom(
      this.http.post<{ message: string }>(`${this.baseUrl}/auth/password-reset`, { email }),
    );
    return res.message;
  }

  /** Set a new password from an emailed link. Every session ends; the person signs in again. */
  async resetPassword(token: string, newPassword: string): Promise<void> {
    await firstValueFrom(
      this.http.post<void>(`${this.baseUrl}/auth/password-reset/confirm`, {
        token,
        new_password: newPassword,
      }),
    );
  }

  /** Exchange the refresh cookie for a new access token. Concurrent callers share one request. */
  refresh(): Promise<string | null> {
    this.refreshInFlight ??= firstValueFrom(
      this.http.post<TokenResponse>(`${this.baseUrl}/auth/refresh`, null, {
        withCredentials: true,
      }),
    )
      .then((res) => {
        this.token.set(res.access_token);
        return res.access_token;
      })
      .catch(() => {
        this.clear();
        return null;
      })
      .finally(() => {
        this.refreshInFlight = null;
      });
    return this.refreshInFlight;
  }

  /** Try to resume a session from the refresh cookie (called once at app start). */
  async restoreSession(): Promise<void> {
    if (await this.refresh()) {
      await this.loadMe().catch(() => this.clear());
    }
  }

  async logout(): Promise<void> {
    try {
      await firstValueFrom(
        this.http.post<void>(`${this.baseUrl}/auth/logout`, null, { withCredentials: true }),
      );
    } finally {
      this.clear();
    }
  }

  private async loadMe(): Promise<Me> {
    const me = await firstValueFrom(this.http.get<Me>(`${this.baseUrl}/auth/me`));
    this.currentUser.set(me);
    return me;
  }

  private clear(): void {
    this.token.set(null);
    this.currentUser.set(null);
  }
}
