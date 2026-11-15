/** Staff accounts and permissions: what a Manager can and can't reach, and deactivation. */
import { expect, test } from '@playwright/test';
import { ADMIN_URL, RUN, staffSignIn, watchConsole } from './env';

test('a new Manager sees only their pages, and deactivation signs them out', async ({
  browser,
}) => {
  const admin = await (await browser.newContext()).newPage();
  const errors = watchConsole(admin);
  await staffSignIn(admin);

  const manager = { name: `Ravi Manager ${RUN}`, email: `ravi.${RUN}@example.com` };
  const password = 'manager-pass-123';
  await admin.click('nav >> text=Staff');
  await admin.click('text=Add staff member');
  await admin.fill('#name', manager.name);
  await admin.fill('#email', manager.email);
  await admin.fill('#password', password);
  await admin.check('label.role:has(strong:text-is("Manager")) input');
  await admin.click('button:has-text("Add staff member")');
  await expect(admin.locator('[role=status]')).toContainText('Staff member added');

  const mgr = await (await browser.newContext()).newPage();
  await staffSignIn(mgr, manager.email, password);
  await expect(mgr.locator('nav a').first()).toBeVisible();
  const menu = (await mgr.locator('nav a').allInnerTexts()).map((t) => t.trim());
  expect(menu).toEqual(expect.arrayContaining(['Dashboard', 'Orders', 'Dispatch']));
  for (const hidden of ['Staff', 'Roles', 'Sales report', 'Audit log']) {
    expect(menu).not.toContain(hidden);
  }
  // Typing the address directly doesn't help: the page is refused.
  await mgr.goto(`${ADMIN_URL}/staff`);
  await expect(mgr).toHaveURL(/\/forbidden$/);

  // Deactivate: their next request is refused and they are back at sign-in.
  await admin.click('button:has-text("Deactivate…")');
  await admin.click('button:has-text("Yes, deactivate")');
  await expect(admin.locator('[role=status]')).toContainText('signed out everywhere');
  await mgr.goto(`${ADMIN_URL}/orders`);
  await expect(mgr).toHaveURL(/\/login/);
  await mgr.fill('#email', manager.email);
  await mgr.fill('#password', password);
  await mgr.click('button[type=submit]');
  await expect(mgr.locator('[role=alert]')).toBeVisible();

  expect(errors).toEqual([]);
});
