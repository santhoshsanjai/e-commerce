/**
 * The whole order journey, end to end:
 * staff list a product -> a buyer orders it (cash on delivery) -> staff dispatch it ->
 * the courier's file marks it delivered -> the buyer sees it -> the sale shows in the report.
 */
import { expect, Page, test } from '@playwright/test';
import ExcelJS from 'exceljs';
import path from 'node:path';
import { ADMIN_URL, BUYER_URL, noSidewaysScroll, RUN, staffSignIn, watchConsole } from './env';

test.describe.configure({ mode: 'serial' });

const category = `E2E Bottles ${RUN}`;
const product = `E2E Steel Bottle ${RUN}`;
const buyer = {
  name: 'Asha Rao',
  email: `asha.${RUN}@example.com`,
  password: 'buyer-pass-123',
};
let orderNumber = '';
let dispatchFile = '';

let staff: Page;
let shopper: Page;
let staffErrors: string[];
let shopperErrors: string[];

test.beforeAll(async ({ browser }) => {
  staff = await (await browser.newContext({ acceptDownloads: true })).newPage();
  shopper = await (await browser.newContext()).newPage();
  staffErrors = watchConsole(staff);
  shopperErrors = watchConsole(shopper);
  await staffSignIn(staff);
});

test.afterAll(() => {
  expect(staffErrors, 'admin console errors').toEqual([]);
  expect(shopperErrors, 'shop console errors').toEqual([]);
});

test('staff add a category and publish a product with an image', async () => {
  await staff.click('nav >> text=Categories');
  await staff.fill('#cname', category);
  await staff.click('text=Add category');
  await expect(staff.getByRole('cell', { name: category, exact: true })).toBeVisible();

  await staff.click('nav >> text=Products');
  await staff.click('text=New product');
  await staff.fill('#name', product);
  await staff.selectOption('#category', { label: category });
  await staff.fill('#price', '499.50');
  await staff.fill('#stock', '5');
  await staff.fill('#short', 'Keeps drinks cold for 24 hours');
  await staff.click('text=Create product');
  await expect(staff.locator('text=Product no. P-')).toBeVisible();

  // Publishing needs an image.
  await staff.fill('#alt', 'Steel bottle, front view');
  await staff.setInputFiles('#file', path.join(__dirname, '..', 'fixtures', 'product.png'));
  await expect(staff.locator('text=Main image')).toBeVisible();
  await staff.click('button:has-text("Publish")');
  await expect(staff.locator('text=Published. It is now visible')).toBeVisible();
});

test('a new buyer finds the product, orders it and sees the confirmation', async () => {
  await shopper.goto(`${BUYER_URL}/?q=${encodeURIComponent(product)}`);
  await shopper.click(`h3:has-text("${product}")`);
  await expect(shopper.locator('h1')).toHaveText(product);
  await expect(shopper.locator('main')).toContainText('₹499.50');

  // Signed out: adding to cart asks them to sign in, and they create an account.
  await shopper.click('button.buy');
  await shopper.waitForURL(/\/login\?returnUrl=/);
  await shopper.click('text=Create account');
  await shopper.fill('#full_name', buyer.name);
  await shopper.fill('#email', buyer.email);
  await shopper.fill('#password', buyer.password);
  await shopper.click('button[type=submit]');
  await expect(shopper.locator('.greeting')).toContainText(buyer.name);

  await shopper.goto(`${BUYER_URL}/?q=${encodeURIComponent(product)}`);
  await shopper.click(`h3:has-text("${product}")`);
  await shopper.click('button.buy');
  await expect(shopper.locator('text=Added to your cart.')).toBeVisible();
  await shopper.click('text=View cart');
  await shopper.selectOption('select[id^=qty-]', '2');
  await expect(shopper.locator('.count')).toHaveText('2');
  await shopper.click('text=Proceed to checkout');

  await shopper.fill('#recipient_name', buyer.name);
  await shopper.fill('#phone', '9876543210');
  await shopper.fill('#line1', '12 MG Road');
  await shopper.fill('#city', 'Bengaluru');
  await shopper.fill('#region', 'Karnataka');
  await shopper.fill('#postal_code', '012345');
  await shopper.click('text=Use this address');
  await expect(shopper.locator('text=Enter a 6-digit PIN code.')).toBeVisible();
  await shopper.fill('#postal_code', '560001');
  await shopper.click('text=Use this address');
  await expect(shopper.locator(`label.address.selected:has-text("${buyer.name}")`)).toBeVisible();
  await shopper.fill('#instructions', 'Call before arriving');
  await shopper.click('button.place');

  await expect(shopper.locator('h1')).toHaveText('Thank you, your order is placed');
  orderNumber = (await shopper.locator('strong:has-text("ORD-")').first().innerText()).trim();
  expect(orderNumber).toMatch(/^ORD-\d{4}-\d+$/);
  await expect(shopper.locator('main')).toContainText('₹999.00');
});

test('the dashboard and order list show the new order', async () => {
  await staff.click('nav >> text=Dashboard');
  await expect(staff.locator('.tile-value').first()).toBeVisible();

  await staff.click('nav >> text=Orders');
  await staff.fill('#q', orderNumber);
  await staff.click('button:has-text("Search")');
  await staff.click(`td a:has-text("${orderNumber}")`);
  await expect(staff.locator('main')).toContainText(buyer.name);
  await expect(staff.locator('main')).toContainText('Call before arriving');
});

test('staff dispatch the order and get the courier file', async () => {
  await staff.click('nav >> text=Dispatch');
  const row = staff.locator('tr', { hasText: orderNumber });
  await row.locator('input[type=checkbox]').check();
  const [download] = await Promise.all([
    staff.waitForEvent('download'),
    staff.click('button:has-text("Create batch")'),
  ]);
  expect(download.suggestedFilename()).toMatch(/^DSP-\d{4}-\d+\.xlsx$/);
  dispatchFile = test.info().outputPath('dispatch.xlsx');
  await download.saveAs(dispatchFile);
  await expect(staff.locator('[role=status]')).toContainText('DSP-');
});

test('the courier fills in the file and staff import it: the order is delivered', async () => {
  // Fill AWB, status and date the way the courier would, then send it back.
  const book = new ExcelJS.Workbook();
  await book.xlsx.readFile(dispatchFile);
  const sheet = book.worksheets[0];
  let headerRow = 0;
  const col: Record<string, number> = {};
  sheet.eachRow((row, n) => {
    if (headerRow) return;
    row.eachCell((cell, c) => {
      if (cell.text === 'Order No') headerRow = n;
      col[cell.text] = c;
    });
  });
  expect(headerRow, 'header row in the courier file').toBeGreaterThan(0);
  let filled = 0;
  sheet.eachRow((row, n) => {
    if (n > headerRow && row.getCell(col['Order No']).text === orderNumber) {
      row.getCell(col['AWB No']).value = `AWB${RUN}`;
      row.getCell(col['Courier Status']).value = 'Delivered';
      row.getCell(col['Status Date']).value = indiaNow();
      filled++;
    }
  });
  expect(filled).toBe(1);
  const returned = test.info().outputPath('courier-return.xlsx');
  await book.xlsx.writeFile(returned);

  await staff.click('nav >> text=Courier import');
  await staff.setInputFiles('input[type=file]', returned);
  await expect(staff.locator('h2:has-text("Preview")')).toBeVisible();
  await expect(staff.locator('main')).toContainText(orderNumber);
  await staff.click('button:has-text("Apply")');
  await expect(staff.getByText(/1 order updated/)).toBeVisible();

  await staff.click('nav >> text=Orders');
  await staff.fill('#q', orderNumber);
  await staff.click('button:has-text("Search")');
  await expect(staff.locator('tr', { hasText: orderNumber })).toContainText('Delivered');
});

test('the buyer sees the order as delivered', async () => {
  await shopper.click('header >> text=Orders');
  await shopper.click(`text=${orderNumber}`);
  await expect(shopper.locator('main')).toContainText('Delivered');
  await expect(shopper.locator('main')).toContainText(`AWB${RUN}`);
});

test('the sale shows in the sales report and the Excel download', async () => {
  await staff.click('nav >> text=Sales report');
  await staff.click('button:has-text("Last 7 days")');
  await expect(staff.locator('.tile-value').first()).not.toHaveText('₹0.00');
  await expect(staff.locator('main')).toContainText(product);

  const [download] = await Promise.all([
    staff.waitForEvent('download'),
    staff.click('button:has-text("Download Excel")'),
  ]);
  const file = test.info().outputPath('sales.xlsx');
  await download.saveAs(file);
  const book = new ExcelJS.Workbook();
  await book.xlsx.readFile(file);
  expect(book.worksheets.map((s) => s.name)).toEqual([
    'Summary',
    'By period',
    'Products',
    'By state',
    'Orders',
  ]);
  const orders: string[] = [];
  book.getWorksheet('Orders')!.eachRow((row) => orders.push(row.getCell(1).text));
  expect(orders).toContain(orderNumber);
});

test('the audit log recorded the staff actions', async () => {
  await staff.click('nav >> text=Audit log');
  for (const action of ['Courier import confirmed', 'Dispatch batch created']) {
    await staff.selectOption('#action', { label: action });
    await expect(staff.locator('tbody tr').first()).toContainText(action);
  }
});

test('admin pages fit a phone screen', async () => {
  await staff.setViewportSize({ width: 375, height: 800 });
  for (const route of ['/dashboard', '/orders', '/dispatch', '/reports/sales', '/staff']) {
    await staff.goto(`${ADMIN_URL}${route}`);
    await expect(staff.locator('main h1')).toBeVisible();
    await noSidewaysScroll(staff);
  }
});

/** The courier writes dates in India time as DD-MM-YYYY HH:MM. */
function indiaNow(): string {
  const parts = new Intl.DateTimeFormat('en-GB', {
    timeZone: 'Asia/Kolkata',
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  }).formatToParts(new Date());
  const get = (t: string) => parts.find((p) => p.type === t)!.value;
  return `${get('day')}-${get('month')}-${get('year')} ${get('hour')}:${get('minute')}`;
}
