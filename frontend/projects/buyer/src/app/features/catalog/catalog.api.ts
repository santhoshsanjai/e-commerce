import { HttpClient, HttpParams } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import {
  API_BASE_URL,
  Category,
  Page,
  ProductCard,
  ProductDetail,
  ProductSort,
} from '@shop/shared';
import { Observable, shareReplay } from 'rxjs';

export interface ProductQuery {
  q?: string;
  category?: string;
  sort?: ProductSort;
  page?: number;
  pageSize?: number;
}

@Injectable({ providedIn: 'root' })
export class CatalogApi {
  private readonly http = inject(HttpClient);
  private readonly base = inject(API_BASE_URL);

  // Shared by the header, home page and listing; loaded once per visit.
  private readonly categories$ = this.http
    .get<Category[]>(`${this.base}/categories`)
    .pipe(shareReplay({ bufferSize: 1, refCount: false }));

  categories(): Observable<Category[]> {
    return this.categories$;
  }

  products(query: ProductQuery): Observable<Page<ProductCard>> {
    let params = new HttpParams()
      .set('page', query.page ?? 1)
      .set('page_size', query.pageSize ?? 24)
      .set('sort', query.sort ?? 'newest');
    if (query.q) params = params.set('q', query.q);
    if (query.category) params = params.set('category', query.category);
    return this.http.get<Page<ProductCard>>(`${this.base}/products`, { params });
  }

  /** The canonical lookup, by product number (see product-link.ts). */
  productByNumber(productNumber: string): Observable<ProductDetail> {
    return this.http.get<ProductDetail>(
      `${this.base}/products/by-number/${encodeURIComponent(productNumber)}`,
    );
  }

  /** Only for old /products/{slug} links. */
  product(slug: string): Observable<ProductDetail> {
    return this.http.get<ProductDetail>(`${this.base}/products/${encodeURIComponent(slug)}`);
  }
}
