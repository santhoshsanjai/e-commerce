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

  /** The rows that couldn't be applied, as Excel to send back to the courier. */
  async downloadErrorReport(imp: Pick<CourierImport, 'id' | 'file_name'>): Promise<void> {
    const blob = await firstValueFrom(
      this.http.get(`${this.base}/${imp.id}/error-report`, { responseType: 'blob' }),
    );
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `${imp.file_name.replace(/\.xlsx$/i, '')} - rows to fix.xlsx`;
    link.click();
    setTimeout(() => URL.revokeObjectURL(url), 0);
  }

  confirm(id: string): Promise<CourierImportDetail> {
    return firstValueFrom(this.http.post<CourierImportDetail>(`${this.base}/${id}/confirm`, {}));
  }
}
