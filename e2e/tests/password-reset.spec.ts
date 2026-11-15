/** A buyer who forgot their password resets it from the emailed link. */
import { expect, test } from '@playwright/test';
import { BUYER_URL, buyerSignIn, readEmail, RUN, watchConsole } from './env';

test('a buyer resets a forgotten password from the email link', async ({ page }) => {
  const errors = watchConsole(page);
  const email = `forgetful.${RUN}@example.com`;
  const register = await page.request.post(`${BUYER_URL}/api/v1/auth/register`, {
    data: { email, password: 'old-password-1', full_name: 'Kiran Forgetful' },
  });
  expect(register.status()).toBe(201);

  await page.goto(`${BUYER_URL}/login`);
  await page.click('text=Forgot your password?');
  await page.fill('#reset_email', email);
  await page.click('button:has-text("Send reset link")');
  await expect(page.getByRole('status')).toContainText("we've sent a link");

  const text = await readEmail(email, 'Reset your password');
  const link = text.match(/https?:\/\/\S+\/reset-password\?token=[\w-]+/)?.[0];
  expect(link, text).toBeTruthy();
  // Open it on whichever address the tests reach the buyer site at.
  await page.goto(`${BUYER_URL}${new URL(link!).pathname}${new URL(link!).search}`);
  await expect(page).toHaveURL(/\/reset-password$/); // token removed from the address bar
  await page.fill('#reset_new_password', 'new-password-22');
  await page.fill('#reset_confirm_password', 'new-password-22');
  await page.click('button:has-text("Save new password")');
  await expect(page.getByRole('status')).toContainText('signed out on every device');

  // The link works once.
  await page.goto(`${BUYER_URL}${new URL(link!).pathname}${new URL(link!).search}`);
  await page.fill('#reset_new_password', 'another-password-3');
  await page.fill('#reset_confirm_password', 'another-password-3');
  await page.click('button:has-text("Save new password")');
  await expect(page.getByRole('alert')).toContainText('already been used');

  await readEmail(email, 'Your password was changed');
  await buyerSignIn(page, email, 'new-password-22');
  expect(errors.filter((e) => !/status of 400/.test(e))).toEqual([]);
});
