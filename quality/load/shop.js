// Load test for the shop: buyers browsing, searching and filling carts.
//
//   docker run --rm -i --network host -e BASE_URL=http://localhost:4200 grafana/k6:1.4.2 run - <quality/load/shop.js
//
// PROFILE=smoke (default) is a short check that runs in CI. PROFILE=load is the launch test:
// run it against staging, never production, because it registers test buyers (k6-…@example.com).
// The thresholds below are the targets from the implementation plan; k6 exits non-zero when
// one is missed.
import http from 'k6/http';
import { check, group, sleep } from 'k6';

const BASE = (__ENV.BASE_URL || 'http://localhost:4200').replace(/\/$/, '');
const API = `${BASE}/api/v1`;
const PROFILE = __ENV.PROFILE || 'smoke';

const profiles = {
  smoke: {
    browse: { executor: 'constant-vus', vus: 5, duration: '30s' },
    carts: { executor: 'constant-vus', vus: 2, duration: '30s', exec: 'fillCart' },
  },
  load: {
    browse: {
      executor: 'ramping-vus',
      stages: [
        { duration: '2m', target: 100 },
        { duration: '5m', target: 100 },
        { duration: '1m', target: 0 },
      ],
    },
    carts: {
      executor: 'ramping-vus',
      exec: 'fillCart',
      stages: [
        { duration: '2m', target: 20 },
        { duration: '5m', target: 20 },
        { duration: '1m', target: 0 },
      ],
    },
  },
};

export const options = {
  scenarios: profiles[PROFILE],
  thresholds: {
    http_req_failed: ['rate<0.01'],
    'http_req_duration{kind:api}': ['p(95)<500'],
    'http_req_duration{kind:page}': ['p(95)<800'],
    checks: ['rate>0.99'],
  },
};

const page = { tags: { kind: 'page' } };
const api = { tags: { kind: 'api' } };
const json = (params = {}) => ({
  ...params,
  headers: { 'Content-Type': 'application/json', ...(params.headers || {}) },
  tags: { kind: 'api' },
});

/** The products to look at, read once before the test starts. */
export function setup() {
  const products = http.get(`${API}/products?page_size=50`, api).json('items');
  if (!products || products.length === 0) {
    throw new Error(`No products at ${API}/products. Add some first (seed-sample-products).`);
  }
  return { products, run: Date.now().toString(36) };
}

const pick = (list) => list[Math.floor(Math.random() * list.length)];
const SEARCHES = ['mug', 'cotton', 'steel', 'lamp', 'bowl'];

/** Someone looking around: home page, a category, a search, two product pages. */
export default function browse(data) {
  group('home', () => {
    check(http.get(`${BASE}/`, page), { 'home page': (r) => r.status === 200 });
    check(http.get(`${API}/storefront`, api), { storefront: (r) => r.status === 200 });
    check(http.get(`${API}/products?sort=newest&page_size=12`, api), {
      'newest products': (r) => r.status === 200,
    });
  });
  sleep(1);
  group('search', () => {
    const q = pick(SEARCHES);
    check(http.get(`${API}/products?q=${q}&page_size=24`, api), {
      search: (r) => r.status === 200,
    });
  });
  sleep(1);
  group('product', () => {
    for (let i = 0; i < 2; i++) {
      const p = pick(data.products);
      check(http.get(`${BASE}/p/${p.slug}/${p.product_number}`, page), {
        'product page': (r) => r.status === 200,
      });
      check(http.get(`${API}/products/by-number/${p.product_number}`, api), {
        'product details': (r) => r.status === 200,
      });
      sleep(1);
    }
  });
}

let token = null;

/** A signed-in buyer adding to the cart, opening it and taking the item out. Orders are not
 * placed, so stock is untouched. */
export function fillCart(data) {
  if (!token) {
    // Each virtual buyer registers its own account the first time round.
    const buyer = { email: `k6-${data.run}-${__VU}@example.com`, password: `k6-pass-${data.run}` };
    const registered = http.post(
      `${API}/auth/register`,
      JSON.stringify({ ...buyer, full_name: `Load Test ${__VU}` }),
      json(),
    );
    check(registered, { 'test buyer registered': (r) => r.status === 201 });
    const res = http.post(`${API}/auth/login`, JSON.stringify(buyer), json());
    check(res, { 'buyer signed in': (r) => r.status === 200 });
    token = res.json('access_token');
  }
  const auth = { headers: { Authorization: `Bearer ${token}` } };
  const p = pick(data.products.filter((x) => x.availability !== 'OUT_OF_STOCK'));
  const added = http.post(
    `${API}/cart/items`,
    JSON.stringify({ sku_id: p.sku_id, qty: 1 }),
    json(auth),
  );
  check(added, { 'added to cart': (r) => r.status === 200 || r.status === 201 });
  sleep(1);
  check(http.get(`${API}/cart`, { ...auth, tags: { kind: 'api' } }), {
    'cart opened': (r) => r.status === 200,
  });
  sleep(1);
  // Take it out again, so the cart doesn't hit its per-item limit over a long run.
  check(http.del(`${API}/cart/items/${p.sku_id}`, null, { ...auth, tags: { kind: 'api' } }), {
    'removed from cart': (r) => r.status === 200,
  });
  sleep(1);
}
