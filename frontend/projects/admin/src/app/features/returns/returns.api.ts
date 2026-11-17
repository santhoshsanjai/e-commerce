import { HttpClient, HttpParams } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { AdminReturn, API_BASE_URL, Page, RefundMethod, ReturnStatus } from '@shop/shared';
import { Observable } from 'rxjs';

@Injectable({ providedIn: 'root' })
export class ReturnsApi {
  private readonly http = inject(HttpClient);
  private readonly base = `${inject(API_BASE_URL)}/admin/returns`;

  list(page: number, status: ReturnStatus | '', q: string): Observable<Page<AdminReturn>> {
    let params = new HttpParams().set('page', page).set('page_size', 20);
    if (status) params = params.set('status', status);
    if (q) params = params.set('q', q);
    return this.http.get<Page<AdminReturn>>(this.base, { params });
  }

  get(id: string): Observable<AdminReturn> {
    return this.http.get<AdminReturn>(`${this.base}/${id}`);
  }

  approve(id: string, note: string): Observable<AdminReturn> {
    return this.http.post<AdminReturn>(`${this.base}/${id}/approve`, { note });
  }

  reject(id: string, note: string): Observable<AdminReturn> {
    return this.http.post<AdminReturn>(`${this.base}/${id}/reject`, { note });
  }

  receive(id: string, restock: string[]): Observable<AdminReturn> {
    return this.http.post<AdminReturn>(`${this.base}/${id}/receive`, { restock });
  }

  refund(
    id: string,
    body: { amount_minor: number; method: RefundMethod; reference: string },
  ): Observable<AdminReturn> {
    return this.http.post<AdminReturn>(`${this.base}/${id}/refund`, body);
  }
}
