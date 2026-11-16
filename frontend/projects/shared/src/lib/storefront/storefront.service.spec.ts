import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { StorefrontService } from './storefront.service';

describe('StorefrontService', () => {
  let service: StorefrontService;
  let http: HttpTestingController;
  const root = document.documentElement;

  beforeEach(() => {
    localStorage.clear();
    root.removeAttribute('style');
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting()],
    });
    service = TestBed.inject(StorefrontService);
    http = TestBed.inject(HttpTestingController);
  });

  it('applies saved colours as CSS variables and remembers them', async () => {
    const loading = service.load();
    http.expectOne('/api/v1/storefront').flush({
      store_name: 'Maison',
      announcement: 'Hello',
      colors: { primary: '#112233', 'not-a-token': '#445566', accent: 'red' },
    });
    await loading;
    expect(service.settings().store_name).toBe('Maison');
    expect(root.style.getPropertyValue('--color-primary')).toBe('#112233');
    // Unknown names and anything that isn't a plain hex colour never reach the page.
    expect(root.style.getPropertyValue('--color-not-a-token')).toBe('');
    expect(root.style.getPropertyValue('--color-accent')).toBe('');
    expect(JSON.parse(localStorage.getItem('storefront')!).store_name).toBe('Maison');
  });

  it('removes an override when it is no longer set', () => {
    service.set({ store_name: 'Shop', announcement: '', colors: { primary: '#112233' } });
    service.set({ store_name: 'Shop', announcement: '', colors: {} });
    expect(root.style.getPropertyValue('--color-primary')).toBe('');
  });

  it('keeps the defaults when the API is unreachable', async () => {
    const loading = service.load();
    http.expectOne('/api/v1/storefront').flush('down', { status: 503, statusText: 'Down' });
    await loading;
    expect(service.settings()).toEqual({ store_name: 'Shop', announcement: '', colors: {} });
  });
});
