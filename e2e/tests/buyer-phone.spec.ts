/** The shop on a phone: browsing, cart and account fit the screen. */
import { expect, test } from '@playwright/test';
import { BUYER_URL, noSidewaysScroll, RUN, watchConsole } from './env';

test('the shop works on a phone', async ({ page }) => {
  const errors = watchConsole(page);
  await page.goto(BUYER_URL);
  await expect(page.locator('a.card-link').first()).toBeVisible();
  await noSidewaysScroll(page);

  await page.locator('a.card-link').first().click();
  await expect(page.locator('button.buy')).toBeVisible();
  await noSidewaysScroll(page);

  await page.goto(`${BUYER_URL}/register`);
  await page.fill('#full_name', 'Phone Buyer');
  await page.fill('#email', `phone.${RUN}@example.com`);
  await page.fill('#password', 'buyer-pass-123');
  await page.click('button[type=submit]');
  await expect(page.locator('.greeting, header a:has-text("Account")').first()).toBeVisible();

  for (const route of ['/cart', '/orders', '/account']) {
    await page.goto(`${BUYER_URL}${route}`);
    await expect(page.locator('main h1, h1').first()).toBeVisible();
    await noSidewaysScroll(page);
  }
  expect(errors).toEqual([]);
});
