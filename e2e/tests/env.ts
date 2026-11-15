import { expect, Page } from '@playwright/test';

export const BUYER_URL = process.env.BUYER_URL ?? 'http://localhost:4200';
export const ADMIN_URL = process.env.ADMIN_URL ?? 'http://localhost:4300';
export const ADMIN_EMAIL = process.env.E2E_ADMIN_EMAIL ?? 'admin@example.com';
export const ADMIN_PASSWORD = process.env.E2E_ADMIN_PASSWORD ?? 'super-admin-pass-1';

/** Something unique per run, so the suite can run again on the same database. */
export const RUN = Date.now().toString(36);

export async function staffSignIn(page: Page, email = ADMIN_EMAIL, password = ADMIN_PASSWORD) {
  await page.goto(`${ADMIN_URL}/login`);
  await page.fill('#email', email);
  await page.fill('#password', password);
  await page.click('button[type=submit]');
  await expect(page.locator('main h1').first()).toBeVisible();
}

export async function buyerSignIn(page: Page, email: string, password: string) {
  await page.goto(`${BUYER_URL}/login`);
  await page.fill('#email', email);
  await page.fill('#password', password);
  await page.click('button[type=submit]');
  await expect(page.locator('.greeting')).toBeVisible();
}

/** Fail the test on any browser console error, apart from expected 401s while signed out. */
export function watchConsole(page: Page): string[] {
  const errors: string[] = [];
  page.on('console', (m) => {
    if (m.type() === 'error' && !/status of 40[01]/.test(m.text())) errors.push(m.text());
  });
  page.on('pageerror', (e) => errors.push(e.message));
  return errors;
}

export async function noSidewaysScroll(page: Page) {
  const overflow = await page.evaluate(
    () => document.documentElement.scrollWidth > window.innerWidth,
  );
  expect(overflow, 'page scrolls sideways').toBe(false);
}
