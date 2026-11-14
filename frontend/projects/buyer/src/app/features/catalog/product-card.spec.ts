import { TestBed } from '@angular/core/testing';
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
};

describe('ProductCard', () => {
  it('shows price, compare-at price, availability and links to the product', async () => {
    TestBed.configureTestingModule({ imports: [ProductCard], providers: [provideRouter([])] });
    const fixture = TestBed.createComponent(ProductCard);
    fixture.componentRef.setInput('product', PRODUCT);
    await fixture.whenStable();
    const el = fixture.nativeElement as HTMLElement;
    expect(el.querySelector('.price')?.textContent).toContain('₹499.50');
    expect(el.querySelector('s')?.textContent).toContain('₹599.00');
    expect(el.querySelector('.stock')?.textContent?.trim()).toBe('Out of stock');
    expect(el.querySelector('a')?.getAttribute('href')).toBe('/products/steel-bottle');
  });
});
