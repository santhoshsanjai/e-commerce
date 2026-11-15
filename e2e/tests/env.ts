import { expect, Page } from '@playwright/test';
import { createHmac } from 'node:crypto';
import { existsSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { dirname, join } from 'node:path';

export const BUYER_URL = process.env.BUYER_URL ?? 'http://localhost:4200';
export const ADMIN_URL = process.env.ADMIN_URL ?? 'http://localhost:4300';
/** Mailpit (docker-compose) catches the app's emails; its API lets tests read them. */
export const MAILPIT_URL = process.env.MAILPIT_URL ?? 'http://localhost:8025';
export const ADMIN_EMAIL = process.env.E2E_ADMIN_EMAIL ?? 'admin@example.com';
export const ADMIN_PASSWORD = process.env.E2E_ADMIN_PASSWORD ?? 'super-admin-pass-1';

/** Something unique per run, so the suite can run again on the same database. */
export const RUN = Date.now().toString(36);

/**
 * Staff sign-in, including two-step sign-in. The first time an account signs in it sets up the
 * authenticator app; its secret is kept in .auth/totp.json (git-ignored) for later sign-ins.
 */
export async function staffSignIn(page: Page, email = ADMIN_EMAIL, password = ADMIN_PASSWORD) {
  await page.goto(`${ADMIN_URL}/login`);
  await page.fill('#email', email);
  await page.fill('#password', password);
  await page.click('button[type=submit]');
  await page.locator('#mfa_code, nav a').first().waitFor();
  const heading = (await page.locator('main h1').first().textContent()) ?? '';
  if (heading.includes('Set up two-step sign-in')) {
    await page.click("text=Can't scan it?");
    const secret = (await page.getByTestId('mfa-secret').textContent())!.replace(/\s/g, '');
    const step = await nextStep(email);
    await page.fill('#mfa_code', totp(secret, step));
    await page.click('button:has-text("Turn on two-step sign-in")');
    await expect(page.getByTestId('recovery-codes')).toBeVisible();
    saveTotp(email, { secret, lastStep: step });
    await page.click('button:has-text("I\'ve saved them")');
  } else if (heading.includes('Two-step sign-in')) {
    const saved = loadTotp()[email];
    if (!saved) {
      throw new Error(
        `${email} already has two-step sign-in, but its secret isn't in e2e/.auth/totp.json. ` +
          `Reset it with: python -m app.cli reset-mfa --email ${email}`,
      );
    }
    const step = await nextStep(email);
    await page.fill('#mfa_code', totp(saved.secret, step));
    await page.click('button:has-text("Continue")');
    saveTotp(email, { ...saved, lastStep: step });
  }
  await expect(page).not.toHaveURL(/\/login/);
  await expect(page.locator('nav a').first()).toBeVisible();
}

// --- authenticator codes (RFC 6238) for the sign-ins above ---

interface SavedTotp {
  secret: string;
  lastStep: number;
}
const TOTP_FILE = join(__dirname, '..', '.auth', 'totp.json');

function loadTotp(): Record<string, SavedTotp> {
  return existsSync(TOTP_FILE) ? JSON.parse(readFileSync(TOTP_FILE, 'utf8')) : {};
}

function saveTotp(email: string, value: SavedTotp) {
  mkdirSync(dirname(TOTP_FILE), { recursive: true });
  writeFileSync(TOTP_FILE, JSON.stringify({ ...loadTotp(), [email]: value }, null, 2));
}

const currentStep = () => Math.floor(Date.now() / 30_000);

/** A step the API will accept: never one already used (codes are single-use), at most one step
 * ahead of the clock (the drift it allows). Waits for the clock when sign-ins come quickly. */
async function nextStep(email: string): Promise<number> {
  const last = loadTotp()[email]?.lastStep ?? 0;
  while (last + 1 > currentStep() + 1) {
    await new Promise((r) => setTimeout(r, 1000));
  }
  return Math.max(currentStep(), last + 1);
}

function totp(secretBase32: string, step: number): string {
  const alphabet = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ234567';
  let bits = '';
  for (const ch of secretBase32.toUpperCase().replace(/=+$/, '')) {
    bits += alphabet.indexOf(ch).toString(2).padStart(5, '0');
  }
  const key = Buffer.from(bits.match(/.{8}/g)!.map((b) => parseInt(b, 2)));
  const counter = Buffer.alloc(8);
  counter.writeBigUInt64BE(BigInt(step));
  const hmac = createHmac('sha1', key).update(counter).digest();
  const offset = hmac[hmac.length - 1] & 0xf;
  const value = (hmac.readUInt32BE(offset) & 0x7fffffff) % 1_000_000;
  return value.toString().padStart(6, '0');
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
