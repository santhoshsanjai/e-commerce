import { afterNextRender, DestroyRef, Directive, ElementRef, inject, input } from '@angular/core';

/**
 * Fades and lifts an element into view the first time it scrolls on screen.
 * `shrReveal` takes an optional delay in milliseconds, for staggering a row of items.
 * Does nothing for visitors who prefer reduced motion, or where IntersectionObserver is missing.
 */
@Directive({ selector: '[shrReveal]' })
export class RevealDirective {
  readonly shrReveal = input<number | ''>('');
  private readonly el = inject<ElementRef<HTMLElement>>(ElementRef).nativeElement;

  constructor() {
    const destroyRef = inject(DestroyRef);
    afterNextRender(() => {
      if (
        typeof IntersectionObserver === 'undefined' ||
        matchMedia('(prefers-reduced-motion: reduce)').matches
      ) {
        return;
      }
      // Already on screen at first render: show it straight away, without the effect.
      const rect = this.el.getBoundingClientRect();
      if (rect.top < innerHeight && rect.bottom > 0) return;
      const delay = this.shrReveal();
      if (delay) this.el.style.setProperty('--reveal-delay', `${delay}ms`);
      this.el.classList.add('reveal-ready');
      const observer = new IntersectionObserver(
        (entries) => {
          if (entries.some((e) => e.isIntersecting)) {
            this.el.classList.add('revealed');
            observer.disconnect();
          }
        },
        { rootMargin: '0px 0px -8% 0px' },
      );
      observer.observe(this.el);
      destroyRef.onDestroy(() => observer.disconnect());
    });
  }
}
