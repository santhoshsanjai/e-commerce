import { InjectionToken } from '@angular/core';

/** Base URL of the API, e.g. `/api/v1` behind the same origin or a full URL in development. */
export const API_BASE_URL = new InjectionToken<string>('API_BASE_URL', {
  factory: () => '/api/v1',
});
