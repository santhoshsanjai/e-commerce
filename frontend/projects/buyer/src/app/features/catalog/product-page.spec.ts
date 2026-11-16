import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { provideRouter, Router, withComponentInputBinding } from '@angular/router';
import { RouterTestingHarness } from '@angular/router/testing';
import { ProductDetail } from '@shop/shared';
import { ProductPage } from './product-page';

const PRODUCT: ProductDetail = {
  product_number: 'P-000002',
  name: 'Glazed Stoneware Mug, Navy',
  slug: 'glazed-stoneware-mug-navy',
  short_description: '',
  price_minor: 159900,
  compare_at_minor: null,
  currency: 'INR',
  availability: 'IN_STOCK',
  image_url: null,
  image_alt: '',
  sku_id: 'sku-2',
  description: '',
  category: {
    id: 'c1',
    parent_id: null,
    name: 'Kitchen',
    slug: 'kitchen',
    sort_order: 0,
    is_active: true,
  },
  attributes: [],
  media: [],
};

describe('ProductPage addresses', () => {
  let http: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [
        provideRouter(
          [
            { path: 'p/:slug/:productNumber', component: ProductPage },
            { path: 'products/:slug', component: ProductPage },
          ],
          withComponentInputBinding(),
        ),
        provideHttpClient(),
        provideHttpClientTesting(),
      ],
    });
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => document.head.querySelector('link[rel=canonical]')?.remove());

  it('looks the product up by number and fixes an out-of-date slug', async () => {
    const harness = await RouterTestingHarness.create();
    await harness.navigateByUrl('/p/old-name/P-000002');
    http.expectOne('/api/v1/products/by-number/P-000002').flush(PRODUCT);
    await harness.fixture.whenStable();

    expect(TestBed.inject(Router).url).toBe('/p/glazed-stoneware-mug-navy/P-000002');
    // Correcting the slug doesn't fetch the product again.
    http.verify();
    const canonical = document.head.querySelector<HTMLLinkElement>('link[rel=canonical]');
    expect(canonical?.href).toContain('/p/glazed-stoneware-mug-navy/P-000002');
  });

  it('moves an old /products/{slug} link to the canonical address', async () => {
    const harness = await RouterTestingHarness.create();
    await harness.navigateByUrl('/products/glazed-stoneware-mug-navy');
    http.expectOne('/api/v1/products/glazed-stoneware-mug-navy').flush(PRODUCT);
    // The redirect opens the canonical page, which loads the product by number.
    let flushed = 0;
    for (let i = 0; i < 20 && !flushed; i++) {
      await new Promise((resolve) => setTimeout(resolve));
      const requests = http.match('/api/v1/products/by-number/P-000002');
      requests.forEach((r) => r.flush(PRODUCT));
      flushed = requests.length;
    }
    expect(flushed).toBe(1);
    await harness.fixture.whenStable();

    expect(TestBed.inject(Router).url).toBe('/p/glazed-stoneware-mug-navy/P-000002');
  });

  it('shows "Product not found" for an unknown number', async () => {
    const harness = await RouterTestingHarness.create();
    await harness.navigateByUrl('/p/anything/P-999999');
    http
      .expectOne('/api/v1/products/by-number/P-999999')
      .flush({ error: { code: 'product_not_found' } }, { status: 404, statusText: 'Not Found' });
    await harness.fixture.whenStable();
    harness.fixture.detectChanges();

    expect(harness.routeNativeElement?.textContent).toContain('Product not found');
    expect(TestBed.inject(Router).url).toBe('/p/anything/P-999999');
  });
});
