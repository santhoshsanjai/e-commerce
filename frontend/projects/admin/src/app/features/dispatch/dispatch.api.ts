import { HttpClient, HttpParams } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import {
  AdminOrderListItem,
  API_BASE_URL,
  DispatchBatch,
  DispatchBatchDetail,
  Page,
} from '@shop/shared';
import { firstValueFrom, Observable } from 'rxjs';

@Injectable({ providedIn: 'root' })
export class DispatchApi {
  private readonly http = inject(HttpClient);
  private readonly base = `${inject(API_BASE_URL)}/admin/dispatch-batches`;

  eligible(): Observable<AdminOrderListItem[]> {
    return this.http.get<AdminOrderListItem[]>(`${this.base}/eligible-orders`);
  }

  batches(page: number): Observable<Page<DispatchBatch>> {
    const params = new HttpParams().set('page', page).set('page_size', 10);
    return this.http.get<Page<DispatchBatch>>(this.base, { params });
  }

  create(orderIds: string[]): Promise<DispatchBatchDetail> {
    return firstValueFrom(this.http.post<DispatchBatchDetail>(this.base, { order_ids: orderIds }));
  }

  /** The file sits behind the API's permission check, so fetch it with the token, then save it. */
  async download(batch: Pick<DispatchBatch, 'id' | 'file_name'>): Promise<void> {
    const blob = await firstValueFrom(
      this.http.get(`${this.base}/${batch.id}/file`, { responseType: 'blob' }),
    );
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = batch.file_name;
    link.click();
    setTimeout(() => URL.revokeObjectURL(url), 0);
  }
}
