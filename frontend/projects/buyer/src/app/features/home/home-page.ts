import { Component, computed, effect, ElementRef, inject, viewChild } from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';
import { Title } from '@angular/platform-browser';
import { RouterLink } from '@angular/router';
import { Icon, RevealDirective, StorefrontService } from '@shop/shared';
import { catchError, map, of } from 'rxjs';
import { CatalogApi } from '../catalog/catalog.api';
import { ProductCard } from '../catalog/product-card';

@Component({
  selector: 'buy-home-page',
  imports: [RouterLink, Icon, RevealDirective, ProductCard],
  templateUrl: './home-page.html',
  styleUrl: './home-page.scss',
})
export class HomePage {
  private readonly api = inject(CatalogApi);
  protected readonly storefront = inject(StorefrontService);

  protected readonly newest = toSignal(
    this.api.products({ sort: 'newest', pageSize: 12 }).pipe(
      map((page) => page.items),
      catchError(() => of([])),
    ),
  );
  protected readonly heroImages = computed(() =>
    (this.newest() ?? []).filter((p) => p.image_url).slice(0, 3),
  );
  protected readonly categories = toSignal(
    this.api.categories().pipe(
      map((all) => all.filter((c) => !c.parent_id).slice(0, 6)),
      catchError(() => of([])),
    ),
  );
  protected readonly skeletons = [0, 1, 2, 3];

  private readonly rail = viewChild<ElementRef<HTMLElement>>('rail');

  constructor() {
    const title = inject(Title);
    effect(() => title.setTitle(this.storefront.settings().store_name));
  }

  protected scrollRail(direction: 1 | -1): void {
    const el = this.rail()?.nativeElement;
    if (!el) return;
    const reduce = matchMedia('(prefers-reduced-motion: reduce)').matches;
    el.scrollBy({ left: direction * el.clientWidth * 0.85, behavior: reduce ? 'auto' : 'smooth' });
  }
}
