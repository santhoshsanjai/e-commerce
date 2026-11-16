import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { provideRouter } from '@angular/router';
import { ProductCard as Card } from '@shop/shared';
import { ProductCard } from './product-card';

const PRODUCT: Card = {
  product_number: 'P-000001',
  name: 'Steel Bottle',
  slug: 'steel-bottle',
  short_description: '',
  price_minor: 49950,
  compare_at_minor: 59900,
  currency: 'INR',
  availability: 'OUT_OF_STOCK',
  image_url: null,
  image_alt: 'Steel Bottle',
  sku_id: '00000000-0000-0000-0000-000000000001',
};

async function render(product: Card): Promise<HTMLElement> {
  TestBed.configureTestingModule({
    imports: [ProductCard],
    providers: [provideRouter([]), provideHttpClient(), provideHttpClientTesting()],
  });
  const fixture = TestBed.createComponent(ProductCard);
  fixture.componentRef.setInput('product', product);
  await fixture.whenStable();
  return fixture.nativeElement as HTMLElement;
}

describe('ProductCard', () => {
  it('shows price, compare-at price, availability and links to the product', async () => {
    const el = await render(PRODUCT);
    expect(el.querySelector('.price')?.textContent).toContain('₹499.50');
    expect(el.querySelector('s')?.textContent).toContain('₹599.00');
    expect(el.querySelector('.badge')?.textContent?.trim()).toBe('Sold out');
    expect(el.querySelector('a')?.getAttribute('href')).toBe('/p/steel-bottle/P-000001');
  });

  it('shows the discount on a sale item that is in stock', async () => {
    const el = await render({ ...PRODUCT, availability: 'IN_STOCK' });
    expect(el.querySelector('.badge')?.textContent?.trim()).toBe('−17%');
  });
});
