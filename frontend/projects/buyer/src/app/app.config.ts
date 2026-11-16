import { provideHttpClient, withFetch, withInterceptors } from '@angular/common/http';
import {
  ApplicationConfig,
  inject,
  provideAppInitializer,
  provideBrowserGlobalErrorListeners,
} from '@angular/core';
import {
  provideRouter,
  withComponentInputBinding,
  withInMemoryScrolling,
  withViewTransitions,
} from '@angular/router';
import { AuthService, authInterceptor, StorefrontService } from '@shop/shared';
import { routes } from './app.routes';

export const appConfig: ApplicationConfig = {
  providers: [
    provideBrowserGlobalErrorListeners(),
    provideRouter(
      routes,
      withComponentInputBinding(),
      withInMemoryScrolling({ scrollPositionRestoration: 'enabled' }),
      // Cross-fade between pages where the browser supports it. The animation is switched off
      // for reduced motion in _base.scss.
      withViewTransitions({ skipInitialTransition: true }),
    ),
    provideHttpClient(withFetch(), withInterceptors([authInterceptor])),
    provideAppInitializer(() => inject(AuthService).restoreSession()),
    provideAppInitializer(() => {
      void inject(StorefrontService).load();
    }),
  ],
};
