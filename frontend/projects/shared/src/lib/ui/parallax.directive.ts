import { afterNextRender, DestroyRef, Directive, ElementRef, inject } from '@angular/core';

/**
 * Follows the pointer across the host and exposes its position as two CSS variables,
 * `--px` and `--py`, each from -1 to 1 (0 is the centre). Children use them for depth,
 * for example `translate: calc(var(--px) * 12px) calc(var(--py) * 12px)`.
 * Updates once per frame, eases back to the centre when the pointer leaves, and does nothing
 * on touch screens or for visitors who prefer reduced motion.
 */
@Directive({ selector: '[shrParallax]' })
export class ParallaxDirective {
  private readonly el = inject<ElementRef<HTMLElement>>(ElementRef).nativeElement;

  constructor() {
    const destroyRef = inject(DestroyRef);
    afterNextRender(() => {
      if (
        !matchMedia('(hover: hover) and (pointer: fine)').matches ||
        matchMedia('(prefers-reduced-motion: reduce)').matches
      ) {
        return;
      }
      let frame = 0;
      let x = 0;
      let y = 0;
      const apply = () => {
        frame = 0;
        this.el.style.setProperty('--px', x.toFixed(3));
        this.el.style.setProperty('--py', y.toFixed(3));
      };
      const schedule = () => {
        if (!frame) frame = requestAnimationFrame(apply);
      };
      const move = (e: PointerEvent) => {
        const r = this.el.getBoundingClientRect();
        x = ((e.clientX - r.left) / r.width) * 2 - 1;
        y = ((e.clientY - r.top) / r.height) * 2 - 1;
        schedule();
      };
      const leave = () => {
        x = 0;
        y = 0;
        schedule();
      };
      this.el.addEventListener('pointermove', move, { passive: true });
      this.el.addEventListener('pointerleave', leave, { passive: true });
      destroyRef.onDestroy(() => {
        cancelAnimationFrame(frame);
        this.el.removeEventListener('pointermove', move);
        this.el.removeEventListener('pointerleave', leave);
      });
    });
  }
}
