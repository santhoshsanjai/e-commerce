import { defineConfig, devices } from '@playwright/test';

/**
 * The tests drive the real apps through nginx, exactly as a customer and a staff member would.
 * Point them at any stack with BUYER_URL / ADMIN_URL (defaults: `docker compose up`).
 */
export default defineConfig({
  testDir: './tests',
  // One shop, one database: the journeys build on each other, so run them in order.
  fullyParallel: false,
  workers: 1,
  timeout: 60_000,
  expect: { timeout: 10_000 },
  retries: process.env.CI ? 1 : 0,
  forbidOnly: !!process.env.CI,
  reporter: process.env.CI ? [['list'], ['html', { open: 'never' }]] : 'list',
  use: {
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
    locale: 'en-IN',
    timezoneId: 'Asia/Kolkata',
  },
  projects: [
    { name: 'desktop', use: { ...devices['Desktop Chrome'] }, testIgnore: /buyer-phone\.spec\.ts/ },
    {
      name: 'phone',
      use: { ...devices['Pixel 7'] },
      // Phone run covers the buyer journey and layout only.
      testMatch: /buyer-phone\.spec\.ts/,
    },
  ],
});
