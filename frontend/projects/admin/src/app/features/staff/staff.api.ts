import { HttpClient, HttpParams } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { API_BASE_URL, Page } from '@shop/shared';
import { firstValueFrom, Observable } from 'rxjs';

export interface StaffMember {
  id: string;
  email: string;
  full_name: string;
  phone: string | null;
  is_active: boolean;
  roles: string[];
  role_ids: string[];
  last_login_at: string | null;
  created_at: string;
}

export interface StaffCreate {
  email: string;
  full_name: string;
  phone: string | null;
  password: string;
  role_ids: string[];
}

export interface StaffUpdate {
  full_name?: string;
  phone?: string | null;
  role_ids?: string[];
  is_active?: boolean;
}

export interface StaffQuery {
  q: string;
  role_id: string;
  status: '' | 'active' | 'inactive';
  page: number;
}

export interface Role {
  id: string;
  name: string;
  description: string;
  is_system: boolean;
  permissions: string[];
  user_count: number;
}

export interface RoleInput {
  name?: string;
  description?: string;
  permissions?: string[];
}

export interface PermissionInfo {
  key: string;
  description: string;
}

export const SUPER_ADMIN = 'Super Admin';
export const STAFF_PAGE_SIZE = 20;

@Injectable({ providedIn: 'root' })
export class StaffApi {
  private readonly http = inject(HttpClient);
  private readonly base = inject(API_BASE_URL);

  list(query: StaffQuery): Observable<Page<StaffMember>> {
    let params = new HttpParams().set('page', query.page).set('page_size', STAFF_PAGE_SIZE);
    if (query.q) params = params.set('q', query.q);
    if (query.role_id) params = params.set('role_id', query.role_id);
    if (query.status) params = params.set('status', query.status);
    return this.http.get<Page<StaffMember>>(`${this.base}/admin/staff`, { params });
  }

  get(id: string): Observable<StaffMember> {
    return this.http.get<StaffMember>(`${this.base}/admin/staff/${id}`);
  }

  create(body: StaffCreate): Promise<StaffMember> {
    return firstValueFrom(this.http.post<StaffMember>(`${this.base}/admin/staff`, body));
  }

  update(id: string, body: StaffUpdate): Promise<StaffMember> {
    return firstValueFrom(this.http.patch<StaffMember>(`${this.base}/admin/staff/${id}`, body));
  }

  resetPassword(id: string, password: string): Promise<void> {
    return firstValueFrom(
      this.http.post<void>(`${this.base}/admin/staff/${id}/password`, { password }),
    );
  }

  roles(): Observable<Role[]> {
    return this.http.get<Role[]>(`${this.base}/admin/roles`);
  }

  permissions(): Observable<PermissionInfo[]> {
    return this.http.get<PermissionInfo[]>(`${this.base}/admin/permissions`);
  }

  createRole(body: RoleInput): Promise<Role> {
    return firstValueFrom(this.http.post<Role>(`${this.base}/admin/roles`, body));
  }

  updateRole(id: string, body: RoleInput): Promise<Role> {
    return firstValueFrom(this.http.patch<Role>(`${this.base}/admin/roles/${id}`, body));
  }

  deleteRole(id: string): Promise<void> {
    return firstValueFrom(this.http.delete<void>(`${this.base}/admin/roles/${id}`));
  }
}
