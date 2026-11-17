import { HttpClient } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { API_BASE_URL, OrderStatus } from '@shop/shared';
import { Observable } from 'rxjs';

export interface DaySales {
  day: string;
  orders: number;
  sales_minor: number;
}

export interface DashboardData {
  currency: string;
  today: DaySales;
  last_7_days: DaySales[];
  cod_with_courier_minor: number;
  status_counts: Record<OrderStatus, number>;
  attention: {
    awaiting_dispatch: number;
    delivery_failed: number;
    on_hold: number;
    returning: number;
    imports_not_applied: number;
    returns_open: number;
    low_stock: { product_id: string; product_number: string; name: string; stock_qty: number }[];
  };
}

@Injectable({ providedIn: 'root' })
export class DashboardApi {
  private readonly http = inject(HttpClient);
  private readonly base = inject(API_BASE_URL);

  load(): Observable<DashboardData> {
    return this.http.get<DashboardData>(`${this.base}/admin/dashboard`);
  }
}
