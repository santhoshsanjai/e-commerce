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
