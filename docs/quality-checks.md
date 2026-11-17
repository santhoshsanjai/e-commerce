# Quality checks: security, load, speed and accessibility

Every pull request runs these in CI against the full stack (`docker compose`). Reports are kept
for 14 days as the **quality-reports** artifact of the run.

| Check | Tool | Where | Fails the run when |
|---|---|---|---|
| Security scan | OWASP ZAP 2.17 | CI job "Security scan, load test and Lighthouse" | any finding not accepted in `quality/zap/rules.tsv` |
| Load test (smoke) | k6 | same job | error rate ≥ 1%, API p95 ≥ 500 ms, page p95 ≥ 800 ms |
| Speed and SEO | Lighthouse CI | same job | accessibility < 0.95, best practices or SEO < 0.9, layout shift > 0.1 (performance < 0.8 only warns) |
| Accessibility | axe-core in Playwright | "End-to-end" job, `e2e/tests/site-accessibility.spec.ts` | any serious or critical WCAG 2.1 A/AA problem on the main pages of either app |

## Security scan (ZAP)
- The shop and the admin portal get a passive baseline scan. The API gets an active scan of
  every endpoint in its OpenAPI description (which is switched off in production).
- Accepted findings, each with its reason, are in `quality/zap/rules.tsv` (see
  `quality/zap/README.md`). Everything else must be fixed, not added there.
- Run locally against `docker compose up`:
  ```
  docker run --rm --network host -v "$PWD/quality:/zap/wrk:rw" zaproxy/zap-stable:2.17.0 \
    zap-baseline.py -t http://localhost:4200 -j -c zap/rules.tsv -r zap-shop.html
  ```
- Before launch, also run the baseline scan against staging (`-t https://staging…`). Never run
  the API (active) scan against production: it sends attack payloads.

## Load test (k6)
`quality/load/shop.js` simulates buyers browsing, searching and adding to the cart. No orders
are placed, so stock doesn't change.
- **smoke** (default, CI): 7 virtual users for 30 seconds.
- **load** (before launch, against staging): ramps to 100 browsing and 20 cart users and holds
  for 5 minutes. It registers test buyers named `k6-…@example.com`.
  ```
  docker run --rm -i -e BASE_URL=https://staging.example.com -e PROFILE=load \
    grafana/k6:1.4.2 run - < quality/load/shop.js
  ```
  Watch the API's CPU, database connections and the 5xx alarm while it runs.

## Lighthouse
Home, shop and one product page, desktop settings, median of 3 runs. Locally:
`cd quality && npm ci && npx lhci autorun --collect.url=http://localhost:4200/`.

## Accessibility
The axe check covers the shop (signed out and signed in, including cart and checkout) and every
admin section. Automated checks catch roughly a third of real problems, so before launch also:
- go through checkout using only the keyboard;
- read the product page and checkout with a screen reader (NVDA or VoiceOver);
- zoom to 200% and check nothing is cut off.

## Found and fixed when these checks were added
- Two cart requests at once for a new buyer gave a server error (k6). Cart creation is now safe
  under concurrent requests.
- A search containing a NUL character gave a server error (ZAP). Such input is now a 400.
- Colour contrast was fine at rest; text measured mid fade-in is not a real problem. Five real
  problems were fixed: chart bars with labels inside an image role, cart and "Add to cart" names
  that didn't include their visible text, and cart thumbnails that were unnamed links.
- The shop and home pages jumped as content loaded (layout shift 0.56 and 0.33); now 0.001.
