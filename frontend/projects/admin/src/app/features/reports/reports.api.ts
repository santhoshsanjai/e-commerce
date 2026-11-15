import { HttpClient, HttpParams } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { API_BASE_URL } from '@shop/shared';
import { firstValueFrom, Observable } from 'rxjs';

export type GroupBy = 'day' | 'week' | 'month';

export interface ReportQuery {
  date_from: string;
  date_to: string;
  group_by: GroupBy;
}

export interface PeriodRow {
  start: string;
  label: string;
  orders: number;
  sales_minor: number;
  items_sold: number;
}

export interface SalesReport {
  currency: string;
  date_from: string;
  date_to: string;
  group_by: GroupBy;
  summary: {
    orders: number;
    sales_minor: number;
    avg_order_minor: number;
    items_sold: number;
    delivered_orders: number;
    delivered_minor: number;
    cod_collected_minor: number;
    cancelled_orders: number;
    cancelled_minor: number;
    returned_orders: number;
    returned_minor: number;
  };
  periods: PeriodRow[];
  top_products: {
    product_number: string;
    product_name: string;
    qty: number;
    sales_minor: number;
  }[];
  regions: { region: string; orders: number; sales_minor: number }[];
}

@Injectable({ providedIn: 'root' })
export class ReportsApi {
  private readonly http = inject(HttpClient);
  private readonly base = `${inject(API_BASE_URL)}/admin/reports/sales`;

  private params(q: ReportQuery): HttpParams {
    return new HttpParams()
      .set('date_from', q.date_from)
      .set('date_to', q.date_to)
      .set('group_by', q.group_by);
  }

  sales(q: ReportQuery): Observable<SalesReport> {
    return this.http.get<SalesReport>(this.base, { params: this.params(q) });
  }

  async download(q: ReportQuery): Promise<void> {
    const blob = await firstValueFrom(
      this.http.get(`${this.base}/export`, { params: this.params(q), responseType: 'blob' }),
    );
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `sales-${q.date_from.replaceAll('-', '')}-${q.date_to.replaceAll('-', '')}.xlsx`;
    link.click();
    setTimeout(() => URL.revokeObjectURL(url), 0);
  }
}
