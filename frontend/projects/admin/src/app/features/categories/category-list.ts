import { Component, inject, signal } from '@angular/core';
import { rxResource } from '@angular/core/rxjs-interop';
import { FormsModule } from '@angular/forms';
import { apiErrorMessage, AuthService, Category, HasPermissionDirective } from '@shop/shared';
import { firstValueFrom } from 'rxjs';
import { AdminCatalogApi } from '../products/admin-catalog.api';

@Component({
  selector: 'adm-category-list',
  imports: [FormsModule, HasPermissionDirective],
  template: `
    <div class="page-head"><h1>Categories</h1></div>
    @if (error()) {
      <div class="alert-error" role="alert">{{ error() }}</div>
    }
    <form *shrHasPermission="'categories.manage'" class="filters card" (ngSubmit)="create()">
      <label class="visually-hidden" for="cname">Category name</label>
      <input id="cname" name="name" placeholder="New category name" [(ngModel)]="name" required />
      <label class="visually-hidden" for="cparent">Parent category</label>
      <select id="cparent" name="parent" [(ngModel)]="parentId">
        <option [ngValue]="null">No parent (top level)</option>
        @for (c of categories.value() ?? []; track c.id) {
          <option [ngValue]="c.id">{{ c.name }}</option>
        }
      </select>
      <button class="btn" type="submit" [disabled]="!name.trim()">Add category</button>
    </form>
    <div class="card table-wrap">
      <table>
        <thead>
          <tr>
            <th scope="col">Name</th>
            <th scope="col">Slug</th>
            <th scope="col">Parent</th>
            <th scope="col">Shown in shop</th>
          </tr>
        </thead>
        <tbody>
          @for (c of categories.value() ?? []; track c.id) {
            <tr>
              <td>{{ c.name }}</td>
              <td>{{ c.slug }}</td>
              <td>{{ parentName(c) }}</td>
              <td>
                <label>
                  <input
                    type="checkbox"
                    [checked]="c.is_active"
                    [disabled]="!canManage()"
                    (change)="toggle(c)"
                  />
                  <span class="visually-hidden">Show {{ c.name }} in shop</span>
                  {{ c.is_active ? 'Yes' : 'No' }}
                </label>
              </td>
            </tr>
          } @empty {
            <tr>
              <td colspan="4" class="empty">
                {{ categories.isLoading() ? 'Loading…' : 'No categories yet.' }}
              </td>
            </tr>
          }
        </tbody>
      </table>
    </div>
  `,
  styleUrl: '../products/admin-table.scss',
  styles: `
    form.card {
      margin-bottom: var(--space-4);
      padding: var(--space-4);
    }
  `,
})
export class CategoryList {
  private readonly api = inject(AdminCatalogApi);
  private readonly auth = inject(AuthService);

  protected name = '';
  protected parentId: string | null = null;
  protected readonly error = signal<string | null>(null);
  protected readonly categories = rxResource({ stream: () => this.api.categories() });

  protected canManage(): boolean {
    return this.auth.hasPermission('categories.manage');
  }

  protected parentName(c: Category): string {
    return this.categories.value()?.find((p) => p.id === c.parent_id)?.name ?? '—';
  }

  protected async create(): Promise<void> {
    await this.run(() =>
      firstValueFrom(this.api.createCategory({ name: this.name.trim(), parent_id: this.parentId })),
    );
    this.name = '';
    this.parentId = null;
  }

  protected async toggle(c: Category): Promise<void> {
    await this.run(() =>
      firstValueFrom(this.api.updateCategory(c.id, { is_active: !c.is_active })),
    );
  }

  private async run(action: () => Promise<unknown>): Promise<void> {
    this.error.set(null);
    try {
      await action();
      this.categories.reload();
    } catch (err) {
      this.error.set(apiErrorMessage(err));
    }
  }
}
