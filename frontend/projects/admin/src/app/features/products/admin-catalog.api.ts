import { HttpClient, HttpParams } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import {
  AdminProduct,
  AdminProductListItem,
  API_BASE_URL,
  Category,
  Page,
  ProductInput,
  ProductStatus,
} from '@shop/shared';
import { Observable } from 'rxjs';

@Injectable({ providedIn: 'root' })
export class AdminCatalogApi {
  private readonly http = inject(HttpClient);
  private readonly base = `${inject(API_BASE_URL)}/admin`;

  categories(): Observable<Category[]> {
    return this.http.get<Category[]>(`${this.base}/categories`);
  }

  createCategory(body: { name: string; parent_id: string | null }): Observable<Category> {
    return this.http.post<Category>(`${this.base}/categories`, body);
  }

  updateCategory(id: string, body: Partial<Category>): Observable<Category> {
    return this.http.patch<Category>(`${this.base}/categories/${id}`, body);
  }

  products(query: {
    q?: string;
    status?: ProductStatus | '';
    page: number;
  }): Observable<Page<AdminProductListItem>> {
    let params = new HttpParams().set('page', query.page).set('page_size', 20);
    if (query.q) params = params.set('q', query.q);
    if (query.status) params = params.set('status', query.status);
    return this.http.get<Page<AdminProductListItem>>(`${this.base}/products`, { params });
  }

  product(id: string): Observable<AdminProduct> {
    return this.http.get<AdminProduct>(`${this.base}/products/${id}`);
  }

  createProduct(body: ProductInput): Observable<AdminProduct> {
    return this.http.post<AdminProduct>(`${this.base}/products`, body);
  }

  updateProduct(id: string, body: Partial<ProductInput>): Observable<AdminProduct> {
    return this.http.patch<AdminProduct>(`${this.base}/products/${id}`, body);
  }

  changeStatus(id: string, action: 'publish' | 'unpublish' | 'archive'): Observable<AdminProduct> {
    return this.http.post<AdminProduct>(`${this.base}/products/${id}/${action}`, null);
  }

  uploadImage(id: string, file: File, altText: string): Observable<AdminProduct> {
    const form = new FormData();
    form.append('file', file);
    form.append('alt_text', altText);
    return this.http.post<AdminProduct>(`${this.base}/products/${id}/media`, form);
  }

  deleteMedia(id: string, mediaId: string): Observable<AdminProduct> {
    return this.http.delete<AdminProduct>(`${this.base}/products/${id}/media/${mediaId}`);
  }
}
