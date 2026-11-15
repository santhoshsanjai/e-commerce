import { Component, input } from '@angular/core';
import { ProductStatus } from '@shop/shared';

const LABELS: Record<ProductStatus, string> = {
  DRAFT: 'Draft',
  PUBLISHED: 'Published',
  ARCHIVED: 'Archived',
};

@Component({
  selector: 'adm-status-chip',
  template: `<span class="chip" [class]="status().toLowerCase()">{{ labels[status()] }}</span>`,
  styles: `
    .chip {
      display: inline-block;
      padding: 2px var(--space-2);
      border-radius: 999px;
      font-size: var(--font-size-sm);
      font-weight: 600;
      background: var(--color-background);
      color: var(--color-muted);
      border: 1px solid var(--color-border);
    }
    .published {
      color: var(--color-success);
      border-color: currentColor;
    }
    .archived {
      color: var(--color-danger);
      border-color: currentColor;
    }
  `,
})
export class StatusChip {
  readonly status = input.required<ProductStatus>();
  protected readonly labels = LABELS;
}
