import { Directive, effect, inject, input, TemplateRef, ViewContainerRef } from '@angular/core';
import { AuthService } from './auth.service';

/**
 * Render the element only when the user holds every listed permission.
 * UI convenience only: the API enforces permissions on every request.
 *
 *   <a *shrHasPermission="'orders.export'" routerLink="/dispatch">Dispatch</a>
 */
@Directive({ selector: '[shrHasPermission]' })
export class HasPermissionDirective {
  private readonly auth = inject(AuthService);
  private readonly template = inject(TemplateRef<unknown>);
  private readonly container = inject(ViewContainerRef);

  readonly shrHasPermission = input.required<string | string[]>();

  private shown = false;

  constructor() {
    effect(() => {
      const keys = this.shrHasPermission();
      const allowed = this.auth.hasPermission(...(Array.isArray(keys) ? keys : [keys]));
      if (allowed && !this.shown) {
        this.container.createEmbeddedView(this.template);
        this.shown = true;
      } else if (!allowed && this.shown) {
        this.container.clear();
        this.shown = false;
      }
    });
  }
}
