import AxeBuilder from '@axe-core/playwright';
import { expect, Page, test } from '@playwright/test';
import { ADMIN_URL, BUYER_URL, buyerSignIn, RUN, staffSignIn } from './env';

/**
 * Automated accessibility check (axe-core, WCAG 2.1 A and AA) on the main pages of both apps.
 * Serious and critical problems fail the run; minor ones are listed in the report only.
 * Automated checks find about a third of real problems, so the launch checklist still has a
 * keyboard and screen reader pass (docs/quality-checks.md).
 */
async function expectAccessible(page: Page, name: string) {
  await page.locator('main h1').first().waitFor();
  // Let fade-ins finish: half-faded text would be measured at its in-between colour.
  await page.waitForLoadState('networkidle');
  // Scroll-linked and looping animations never finish, so wait at most two seconds.
  await page.evaluate(() =>
    Promise.race([
      Promise.all(
        document
          .getAnimations()
          .filter((a) => a.effect?.getTiming().iterations !== Infinity)
          .map((a) => a.finished.catch(() => undefined)),
      ),
      new Promise((resolve) => setTimeout(resolve, 2000)),
    ]),
  );
  const results = await new AxeBuilder({ page })
    .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
    .analyze();
  const blocking = results.violations.filter(
    (v) => v.impact === 'serious' || v.impact === 'critical',
  );
  const summary = blocking.map(
    (v) =>
      `${v.id} (${v.impact}): ${v.help}\n` +
      v.nodes.map((n) => `    ${n.target.join(' ')}: ${n.any[0]?.message ?? ''}`).join('\n'),
  );
  // Soft, so one run lists the problems on every page.
  expect.soft(summary, `accessibility problems on ${name}`).toEqual([]);
}

test('shop pages have no serious accessibility problems', async ({ page }) => {
  await page.goto(`${BUYER_URL}/`);
  await expectAccessible(page, 'home');

  await page.goto(`${BUYER_URL}/shop`);
  await expectAccessible(page, 'shop');

  const res = await page.request.get(`${BUYER_URL}/api/v1/products?page_size=1`);
  const [product] = (await res.json()).items as { slug: string; product_number: string }[];
  if (product) {
    await page.goto(`${BUYER_URL}/p/${product.slug}/${product.product_number}`);
    await expectAccessible(page, 'product page');
  }

  for (const path of ['/login', '/register', '/forgot-password']) {
    await page.goto(`${BUYER_URL}${path}`);
    await expectAccessible(page, path);
  }

  const email = `a11y-${RUN}@example.com`;
  const password = 'a11y-password-1';
  const registered = await page.request.post(`${BUYER_URL}/api/v1/auth/register`, {
    data: { email, password, full_name: 'Access Check' },
  });
  expect(registered.status()).toBe(201);
  await buyerSignIn(page, email, password);
  if (product) {
    await page.goto(`${BUYER_URL}/p/${product.slug}/${product.product_number}`);
    await page.getByRole('button', { name: 'Add to cart' }).first().click();
  }
  for (const path of ['/cart', '/checkout', '/orders', '/account']) {
    await page.goto(`${BUYER_URL}${path}`);
    await expectAccessible(page, path);
  }
});

test('admin portal pages have no serious accessibility problems', async ({ page }) => {
  await page.goto(`${ADMIN_URL}/login`);
  await expectAccessible(page, 'admin sign-in');

  await staffSignIn(page);
  const pages = [
    '/dashboard',
    '/orders',
    '/dispatch',
    '/courier-import',
    '/products',
    '/products/new',
    '/categories',
    '/returns',
    '/reports/sales',
    '/staff',
    '/roles',
    '/storefront',
    '/charges',
    '/audit-log',
  ];
  for (const path of pages) {
    await page.goto(`${ADMIN_URL}${path}`);
    await expectAccessible(page, path);
  }
});
