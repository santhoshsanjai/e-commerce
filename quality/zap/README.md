# Security scan settings (OWASP ZAP)

`rules.tsv` lists the ZAP findings that are accepted, each with its reason. Every other warning
fails the scan. Lines are tab-separated: rule id, `IGNORE` or `OUTOFSCOPE`, then a reason
(`IGNORE`) or a URL pattern (`OUTOFSCOPE`).

- **10055 CSP style-src 'unsafe-inline':** Angular puts component styles inline. Scripts are
  still limited to the site itself, which is what stops injected code.
- **10109 Modern Web Application:** information only; the apps are single-page apps.
- **90022 on /openapi.json:** the API description mentions the courier "Error Report" download,
  which ZAP mistakes for an error page. The description is switched off in production.

Add a line only with a reason someone else can check. How to run the scans is in
[docs/quality-checks.md](../../docs/quality-checks.md).
