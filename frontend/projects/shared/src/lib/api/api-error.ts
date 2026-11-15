import { HttpErrorResponse } from '@angular/common/http';
import { ApiErrorBody } from '../models/auth.models';

/** Turn any HTTP failure into a message safe to show the user. */
export function apiErrorMessage(
  err: unknown,
  fallback = 'Something went wrong. Please try again.',
): string {
  if (err instanceof HttpErrorResponse) {
    if (err.status === 0) {
      return 'Cannot reach the server. Check your connection and try again.';
    }
    const body = err.error as Partial<ApiErrorBody> | null;
    if (body?.error?.message) {
      return body.error.message;
    }
  }
  return fallback;
}
