import { Component, inject } from '@angular/core';
import { AuthService } from '@shop/shared';

/** Placeholder; order and import summaries arrive with Phase 2. */
@Component({
  selector: 'adm-dashboard',
  template: `
    <h1>Dashboard</h1>
    <div class="card">
      <p>Signed in as {{ auth.user()?.email }}.</p>
      <p>Operational summaries (orders by status, pending imports) arrive in a later phase.</p>
    </div>
  `,
})
export class Dashboard {
  protected readonly auth = inject(AuthService);
}
