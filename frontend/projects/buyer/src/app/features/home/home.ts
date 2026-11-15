import { Component } from '@angular/core';

/** Placeholder until the catalogue arrives in Phase 1. */
@Component({
  selector: 'buy-home',
  template: `
    <section class="hero">
      <h1>Welcome</h1>
      <p>Our catalogue is on its way. Create an account now to be ready when it opens.</p>
    </section>
  `,
  styles: `
    .hero {
      padding: var(--space-8) 0;
    }
    h1 {
      font-size: var(--font-size-xl);
      margin: 0 0 var(--space-2);
    }
    p {
      color: var(--color-muted);
    }
  `,
})
export class Home {}
