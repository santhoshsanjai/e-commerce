import { HttpClient, HttpParams } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { API_BASE_URL, CourierImport, CourierImportDetail, Page } from '@shop/shared';
import { firstValueFrom, Observable } from 'rxjs';

@Injectable({ providedIn: 'root' })
export class CourierImportApi {
  private readonly http = inject(HttpClient);
  private readonly base = `${inject(API_BASE_URL)}/admin/courier-imports`;

  imports(page: number): Observable<Page<CourierImport>> {
    const params = new HttpParams().set('page', page).set('page_size', 10);
    return this.http.get<Page<CourierImport>>(this.base, { params });
  }

  get(id: string): Promise<CourierImportDetail> {
    return firstValueFrom(this.http.get<CourierImportDetail>(`${this.base}/${id}`));
  }

  upload(file: File): Promise<CourierImportDetail> {
    const body = new FormData();
    body.append('file', file, file.name);
    return firstValueFrom(this.http.post<CourierImportDetail>(this.base, body));
  }

  confirm(id: string): Promise<CourierImportDetail> {
    return firstValueFrom(this.http.post<CourierImportDetail>(`${this.base}/${id}/confirm`, {}));
  }
}
