import { expect, Page } from '@playwright/test';

export const BUYER_URL = process.env.BUYER_URL ?? 'http://localhost:4200';
export const ADMIN_URL = process.env.ADMIN_URL ?? 'http://localhost:4300';
/** Mailpit (docker-compose) catches the app's emails; its API lets tests read them. */
export const MAILPIT_URL = process.env.MAILPIT_URL ?? 'http://localhost:8025';
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

/** Wait for the newest email to `to` with this subject and return its plain text. */
export async function readEmail(to: string, subject: string): Promise<string> {
  const query = encodeURIComponent(`to:"${to}" subject:"${subject}"`);
  let id: string | undefined;
  await expect
    .poll(
      async () => {
        const res = await fetch(`${MAILPIT_URL}/api/v1/search?query=${query}`);
        id = ((await res.json()) as { messages: { ID: string }[] }).messages[0]?.ID;
        return id;
      },
      { message: `email "${subject}" to ${to}`, timeout: 15_000 },
    )
    .toBeTruthy();
  const res = await fetch(`${MAILPIT_URL}/api/v1/message/${id}`);
  return ((await res.json()) as { Text: string }).Text;
}
