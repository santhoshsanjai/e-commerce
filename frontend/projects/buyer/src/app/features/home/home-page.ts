import { Component, computed, effect, inject } from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';
import { Title } from '@angular/platform-browser';
import { RouterLink } from '@angular/router';
import { Icon, ParallaxDirective, RevealDirective, StorefrontService } from '@shop/shared';
import { catchError, forkJoin, map, of, switchMap } from 'rxjs';
import { CatalogApi } from '../catalog/catalog.api';
import { ProductCard } from '../catalog/product-card';

@Component({
  selector: 'buy-home-page',
  imports: [RouterLink, Icon, ParallaxDirective, RevealDirective, ProductCard],
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
  /** Up to four top-level categories, each shown with the picture of its newest product.
   * Undefined while loading, so the section keeps its space and nothing below it jumps. */
  protected readonly categoryTiles = toSignal(
    this.api.categories().pipe(
      map((all) => all.filter((c) => !c.parent_id).slice(0, 4)),
      switchMap((cats) =>
        cats.length
          ? forkJoin(
              cats.map((category) =>
                this.api.products({ category: category.slug, sort: 'newest', pageSize: 1 }).pipe(
                  map((page) => ({ category, image: page.items[0]?.image_url ?? null })),
                  catchError(() => of({ category, image: null })),
                ),
              ),
            )
          : of([]),
      ),
      catchError(() => of([])),
    ),
  );
  protected readonly skeletons = [0, 1, 2, 3];

  constructor() {
    const title = inject(Title);
    effect(() => title.setTitle(this.storefront.settings().store_name));
  }
}
