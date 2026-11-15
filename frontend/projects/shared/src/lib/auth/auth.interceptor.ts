import { HttpErrorResponse, HttpInterceptorFn, HttpRequest } from '@angular/common/http';
import { inject } from '@angular/core';
import { catchError, from, switchMap, throwError } from 'rxjs';
import { API_BASE_URL } from '../api/api-config';
import { AuthService } from './auth.service';

const withToken = (req: HttpRequest<unknown>, token: string | null) =>
  token ? req.clone({ setHeaders: { Authorization: `Bearer ${token}` } }) : req;

/** Attach the access token to API calls; on a 401, refresh once and retry. */
export const authInterceptor: HttpInterceptorFn = (req, next) => {
  const auth = inject(AuthService);
  const baseUrl = inject(API_BASE_URL);

  if (!req.url.startsWith(baseUrl)) {
    return next(req);
  }
  const isAuthCall = req.url.startsWith(`${baseUrl}/auth/`) && !req.url.endsWith('/auth/me');

  return next(withToken(req, auth.accessToken())).pipe(
    catchError((err: unknown) => {
      if (isAuthCall || !(err instanceof HttpErrorResponse) || err.status !== 401) {
        return throwError(() => err);
      }
      return from(auth.refresh()).pipe(
        switchMap((token) => (token ? next(withToken(req, token)) : throwError(() => err))),
      );
    }),
  );
};
