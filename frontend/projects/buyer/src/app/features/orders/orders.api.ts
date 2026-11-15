import { HttpClient, HttpParams } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { Address, AddressInput, API_BASE_URL, OrderDetail, OrderSummary, Page } from '@shop/shared';
import { Observable } from 'rxjs';

export interface CheckoutInput {
  address_id: string;
  payment_method: 'COD';
  delivery_instructions: string;
}

@Injectable({ providedIn: 'root' })
export class OrdersApi {
  private readonly http = inject(HttpClient);
  private readonly base = inject(API_BASE_URL);

  addresses(): Observable<Address[]> {
    return this.http.get<Address[]>(`${this.base}/me/addresses`);
  }

  createAddress(data: AddressInput): Observable<Address> {
    return this.http.post<Address>(`${this.base}/me/addresses`, data);
  }

  updateAddress(id: string, data: AddressInput): Observable<Address> {
    return this.http.put<Address>(`${this.base}/me/addresses/${id}`, data);
  }

  deleteAddress(id: string): Observable<void> {
    return this.http.delete<void>(`${this.base}/me/addresses/${id}`);
  }

  /** The key stays the same across retries of one attempt, so a retry can never order twice. */
  checkout(data: CheckoutInput, idempotencyKey: string): Observable<OrderDetail> {
    return this.http.post<OrderDetail>(`${this.base}/checkout`, data, {
      headers: { 'Idempotency-Key': idempotencyKey },
    });
  }

  myOrders(page: number): Observable<Page<OrderSummary>> {
    const params = new HttpParams().set('page', page).set('page_size', 10);
    return this.http.get<Page<OrderSummary>>(`${this.base}/me/orders`, { params });
  }

  myOrder(orderNumber: string): Observable<OrderDetail> {
    return this.http.get<OrderDetail>(`${this.base}/me/orders/${encodeURIComponent(orderNumber)}`);
  }
}
