/**
 * Product URLs: /p/{slug}/{product number}, the same shape as large shops use
 * (e.g. /{name}/p/{id}). Only the product number finds the product, because it is unique and
 * never changes; the slug is there for people and search engines, and the product page
 * corrects it when a product has been renamed. Old /products/{slug} links still open the
 * product and are moved to this address.
 */
export function productLink(p: { slug: string; product_number: string }): string[] {
  return ['/p', p.slug, p.product_number];
}
