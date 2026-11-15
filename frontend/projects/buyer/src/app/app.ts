import { Component } from '@angular/core';
import { RouterOutlet } from '@angular/router';
import { Footer } from './layout/footer';
import { Header } from './layout/header';

@Component({
  selector: 'buy-root',
  imports: [RouterOutlet, Header, Footer],
  template: `
    <a class="skip-link" href="#main">Skip to content</a>
    <buy-header />
    <main id="main" class="container" tabindex="-1">
      <router-outlet />
    </main>
    <buy-footer />
  `,
  styles: `
    :host {
      display: flex;
      flex-direction: column;
      min-height: 100vh;
    }
    main {
      flex: 1;
      width: 100%;
      max-width: 1200px;
      margin: 0 auto;
      padding: var(--space-6) var(--space-4);
    }
    .skip-link {
      position: absolute;
      left: -999px;
    }
    .skip-link:focus {
      left: var(--space-4);
      top: var(--space-4);
      z-index: 10;
      background: var(--color-surface);
      padding: var(--space-2) var(--space-4);
    }
  `,
})
export class App {}
