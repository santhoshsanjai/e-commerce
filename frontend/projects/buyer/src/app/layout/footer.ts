import { Component } from '@angular/core';

@Component({
  selector: 'buy-footer',
  template: `<footer>
    <p>&copy; {{ year }} Shop</p>
  </footer>`,
  styles: `
    footer {
      border-top: 1px solid var(--color-border);
      background: var(--color-surface);
      color: var(--color-muted);
      text-align: center;
      padding: var(--space-4);
      font-size: var(--font-size-sm);
    }
  `,
})
export class Footer {
  protected readonly year = new Date().getFullYear();
}
