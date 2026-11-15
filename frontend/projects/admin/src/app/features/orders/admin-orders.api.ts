import { HttpClient, HttpParams } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import {
  AdminOrderDetail,
  AdminOrderListItem,
  API_BASE_URL,
  OrderStatus,
  Page,
} from '@shop/shared';
import { Observable } from 'rxjs';

export interface OrderQuery {
  q: string;
  status: OrderStatus | '';
  dateFrom: string;
  dateTo: string;
  page: number;
}

@Injectable({ providedIn: 'root' })
export class AdminOrdersApi {
  private readonly http = inject(HttpClient);
  private readonly base = `${inject(API_BASE_URL)}/admin/orders`;

  orders(query: OrderQuery): Observable<Page<AdminOrderListItem>> {
    let params = new HttpParams().set('page', query.page).set('page_size', 20);
    if (query.q) params = params.set('q', query.q);
    if (query.status) params = params.set('status', query.status);
    if (query.dateFrom) params = params.set('date_from', query.dateFrom);
    if (query.dateTo) params = params.set('date_to', query.dateTo);
    return this.http.get<Page<AdminOrderListItem>>(this.base, { params });
  }

  order(id: string): Observable<AdminOrderDetail> {
    return this.http.get<AdminOrderDetail>(`${this.base}/${id}`);
  }
}
