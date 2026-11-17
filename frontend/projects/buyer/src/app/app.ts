import { Component, inject } from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';
import { ResolveEnd, Router, RouterOutlet } from '@angular/router';
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
      /* The footer starts below the fold, so it isn't pushed down (a layout shift) when the
         page's content arrives. */
      min-height: 100vh;
    }
    main.contained {
      max-width: var(--container);
      margin: 0 auto;
      padding: var(--space-8) var(--gutter) var(--space-16);
    }
  `,
})
export class App {
  /** Pages such as home run edge to edge; the rest sit in the centred column. */
  protected readonly fullBleed = toSignal(
    inject(Router).events.pipe(
      // ResolveEnd comes before the new page is created, so its first frame already has the
      // right width (deciding on NavigationEnd made the home page jump: a layout shift).
      filter((e) => e instanceof ResolveEnd),
      map((e) => {
        let r = e.state.root;
        while (r.firstChild) r = r.firstChild;
        return !!r.data['fullBleed'];
      }),
    ),
    { initialValue: false },
  );
}
