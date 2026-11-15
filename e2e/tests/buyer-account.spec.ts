/** A buyer manages their account: details, addresses and password. */
import { expect, test } from '@playwright/test';
import { BUYER_URL, buyerSignIn, RUN, watchConsole } from './env';

test('a buyer edits details, manages addresses and changes password', async ({ page }) => {
  const errors = watchConsole(page);
  const email = `neha.${RUN}@example.com`;
  await page.goto(`${BUYER_URL}/register`);
  await page.fill('#full_name', 'Neha');
  await page.fill('#email', email);
  await page.fill('#password', 'buyer-pass-123');
  await page.click('button[type=submit]');
  await expect(page.locator('.greeting')).toBeVisible();

  await page.click('header >> text=Account');
  await page.fill('#profile_name', 'Neha Sharma');
  await page.fill('#profile_phone', '+91 98765 43210');
  await page.click('button:has-text("Save details")');
  await expect(page.locator('text=Your details are saved.')).toBeVisible();
  await expect(page.locator('.greeting')).toContainText('Neha Sharma');

  const addresses = [
    ['Neha Sharma', '9876543210', '4 Park Street', 'Kolkata', 'West Bengal', '700016'],
    ['Neha at work', '9876500000', '22 MG Road', 'Bengaluru', 'Karnataka', '560001'],
  ];
  for (const [name, phone, line1, city, region, pin] of addresses) {
    await page.click('text=+ Add a new address');
    await page.fill('#recipient_name', name);
    await page.fill('#phone', phone);
    await page.fill('#line1', line1);
    await page.fill('#city', city);
    await page.fill('#region', region);
    await page.fill('#postal_code', pin);
    await page.click('button:has-text("Add address")');
    await expect(page.locator('text=Address added.')).toBeVisible();
  }
  await page.click('button:has-text("Make default")');
  await expect(page.locator('.address').first()).toContainText('Neha at work');
  await expect(page.locator('.address').first()).toContainText('Default');

  await page
    .locator('.address', { hasText: 'Kolkata' })
    .locator('button:has-text("Remove")')
    .click();
  await page.click('button:has-text("Yes, remove")');
  await expect(page.locator('.address')).toHaveCount(1);

  await page.fill('#current_password', 'buyer-pass-123');
  await page.fill('#new_password', 'fresh-buyer-pass');
  await page.fill('#confirm_password', 'fresh-buyer-pass');
  await page.click('button:has-text("Change password")');
  await expect(page.locator('text=Password changed.')).toBeVisible();

  await page.click('button:has-text("Sign out")');
  await buyerSignIn(page, email, 'fresh-buyer-pass');
  expect(errors).toEqual([]);
});
