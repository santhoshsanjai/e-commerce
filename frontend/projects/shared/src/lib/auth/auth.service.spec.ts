import { provideHttpClient, withInterceptors } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { HttpClient } from '@angular/common/http';
import { authInterceptor } from './auth.interceptor';
import { AuthService } from './auth.service';
import { Me } from '../models/auth.models';

const ME: Me = {
  id: '1',
  email: 'staff@example.com',
  full_name: 'Staff',
  phone: null,
  user_type: 'STAFF',
  roles: ['Manager'],
  permissions: ['orders.view', 'orders.export'],
  mfa_enabled: false,
};

/** Let pending promise callbacks run. */
const tick = () => new Promise((resolve) => setTimeout(resolve));

describe('AuthService', () => {
  let auth: AuthService;
  let http: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(withInterceptors([authInterceptor])),
        provideHttpClientTesting(),
      ],
    });
    auth = TestBed.inject(AuthService);
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => http.verify());

  async function login(): Promise<void> {
    const done = auth.login({ email: ME.email, password: 'pw' }, 'staff');
    const req = http.expectOne('/api/v1/auth/staff/login');
    expect(req.request.withCredentials).toBe(true);
    req.flush({ access_token: 'tok-1', token_type: 'bearer', expires_in: 900 });
    await tick();
    const me = http.expectOne('/api/v1/auth/me');
    expect(me.request.headers.get('Authorization')).toBe('Bearer tok-1');
    me.flush(ME);
    await done;
  }

  it('logs in staff and exposes permissions', async () => {
    await login();
    expect(auth.isAuthenticated()).toBe(true);
    expect(auth.hasPermission('orders.export')).toBe(true);
    expect(auth.hasPermission('orders.export', 'users.manage')).toBe(false);
  });

  it('uses the buyer login route for buyers', async () => {
    const done = auth.login({ email: 'b@example.com', password: 'pw' }, 'buyer');
    http
      .expectOne('/api/v1/auth/login')
      .flush({ access_token: 't', token_type: 'bearer', expires_in: 900 });
    await tick();
    http.expectOne('/api/v1/auth/me').flush({ ...ME, user_type: 'BUYER', permissions: [] });
    await done;
    expect(auth.hasPermission('orders.view')).toBe(false);
  });

  it('refreshes once on 401 and retries the request', async () => {
    await login();
    const client = TestBed.inject(HttpClient);
    let result: unknown;
    client.get('/api/v1/admin/roles').subscribe((r) => (result = r));

    http.expectOne('/api/v1/admin/roles').flush(null, { status: 401, statusText: 'Unauthorized' });
    await tick();
    http
      .expectOne('/api/v1/auth/refresh')
      .flush({ access_token: 'tok-2', token_type: 'bearer', expires_in: 900 });
    await tick();
    const retry = http.expectOne('/api/v1/admin/roles');
    expect(retry.request.headers.get('Authorization')).toBe('Bearer tok-2');
    retry.flush([]);
    expect(result).toEqual([]);
  });

  it('clears the session when refresh fails', async () => {
    await login();
    const done = auth.refresh();
    http.expectOne('/api/v1/auth/refresh').flush(null, { status: 401, statusText: 'Unauthorized' });
    expect(await done).toBeNull();
    expect(auth.isAuthenticated()).toBe(false);
    expect(auth.accessToken()).toBeNull();
  });

  it('does not attach tokens to non-API URLs', async () => {
    await login();
    TestBed.inject(HttpClient).get('https://cdn.example.com/x.json').subscribe();
    const req = http.expectOne('https://cdn.example.com/x.json');
    expect(req.request.headers.has('Authorization')).toBe(false);
    req.flush({});
  });

  it('updates the signed-in user after a profile change', async () => {
    await login();
    const done = auth.updateProfile({ full_name: 'New Name' });
    const req = http.expectOne('/api/v1/auth/me');
    expect(req.request.method).toBe('PATCH');
    req.flush({ ...ME, full_name: 'New Name' });
    await done;
    expect(auth.user()?.full_name).toBe('New Name');
  });

  it('switches to the fresh token after a password change', async () => {
    await login();
    const done = auth.changePassword('old-pass', 'new-password-1');
    const req = http.expectOne('/api/v1/auth/change-password');
    expect(req.request.withCredentials).toBe(true);
    expect(req.request.body).toEqual({
      current_password: 'old-pass',
      new_password: 'new-password-1',
    });
    req.flush({ access_token: 'tok-2', token_type: 'bearer', expires_in: 900 });
    await done;
    expect(auth.accessToken()).toBe('tok-2');
    expect(auth.isAuthenticated()).toBe(true);
  });
});
