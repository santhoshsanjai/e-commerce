import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';
import { AuthService } from './auth.service';

/**
 * Navigation guards improve the experience only; they are not security.
 * The API rejects any request the user is not allowed to make.
 */
export const authGuard: CanActivateFn = (_route, state) => {
  const auth = inject(AuthService);
  return auth.isAuthenticated()
    ? true
    : inject(Router).createUrlTree(['/login'], { queryParams: { returnUrl: state.url } });
};

export const permissionGuard =
  (...keys: string[]): CanActivateFn =>
  () => {
    const auth = inject(AuthService);
    return auth.hasPermission(...keys) ? true : inject(Router).createUrlTree(['/forbidden']);
  };

/**
 * Where to go after sign-in. Only same-site paths are followed, so a crafted link such as
 * `/login?returnUrl=https://evil.example` cannot send the user elsewhere.
 */
export function safeReturnUrl(url: string | null | undefined): string {
  return url && url.startsWith('/') && !url.startsWith('//') && !url.startsWith('/\\') ? url : '/';
}
