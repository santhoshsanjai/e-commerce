import { Component, inject } from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';
import { ActivatedRoute, NavigationEnd, Router, RouterOutlet } from '@angular/router';
import { filter, map } from 'rxjs';
import { Footer } from './layout/footer';
import { Header } from './layout/header';

@Component({
  selector: 'buy-root',
  imports: [RouterOutlet, Header, Footer],
  template: `
    <a class="skip-link" href="#main">Skip to content</a>
    <buy-header />
    <main id="main" tabindex="-1" [class.contained]="!fullBleed()">
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
      outline: none;
    }
    main.contained {
      max-width: var(--container);
      margin: 0 auto;
      padding: var(--space-8) var(--gutter) var(--space-16);
    }
  `,
})
export class App {
  private readonly route = inject(ActivatedRoute);

  /** Pages such as home run edge to edge; the rest sit in the centred column. */
  protected readonly fullBleed = toSignal(
    inject(Router).events.pipe(
      filter((e) => e instanceof NavigationEnd),
      map(() => {
        let r = this.route.snapshot;
        while (r.firstChild) r = r.firstChild;
        return !!r.data['fullBleed'];
      }),
    ),
    { initialValue: false },
  );
}
