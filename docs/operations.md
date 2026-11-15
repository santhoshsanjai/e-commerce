# Operations runbook

How to tell the shop is healthy, where to look when it isn't, and how to get data back. The AWS
resources named here (alarms, backup bucket, scheduled tasks) are created by the Terraform code in
`infra/` (see [infra/README.md](../infra/README.md)).

## Health checks

| Endpoint | Meaning | Used by |
| --- | --- | --- |
| `GET /health/live` | The API process is up. Never touches the database. Returns the running `version` (git commit). | Container health check (restarts a stuck container) |
| `GET /health/ready` | The database answers **and** its schema is at the migration this code expects. 503 otherwise, with `reason: schema_mismatch` when a migration is missing. | Load balancer target health (no traffic to an instance that isn't ready) |

On AWS each API task runs `alembic upgrade head` before the API starts. If a migration still
hasn't been applied, the API's instances stay "not ready" and the old ones keep serving.

## Logs

The API writes one JSON object per line to stdout (CloudWatch Logs when deployed). Every line has
`ts`, `level`, `logger`, `msg` and `request_id`. Each API request adds one `app.access` line with
`method`, `path`, `status`, `duration_ms` and `client_ip`. Health checks aren't logged.

The `request_id` is also returned to the browser in the `X-Request-ID` header and in every error
response, so a buyer's or staff member's error message can be traced to its log lines.

CloudWatch Logs Insights queries:

```
# Server errors in the last hour, newest first
fields ts, path, status, request_id | filter logger = "app.access" and status >= 500 | sort ts desc

# Slowest endpoints
filter logger = "app.access" | stats pct(duration_ms, 95) as p95, count() as n by path | sort p95 desc

# Everything for one request
filter request_id = "paste-id-here" | sort ts asc

# Errors and tracebacks
filter level = "ERROR" | fields ts, msg, exc
```

Logs never contain passwords, tokens, reset links or authenticator secrets. Emails are logged only
by subject.

## Alerts

All alarms notify one SNS topic, subscribed by email (and optionally SMS). Thresholds to start with:

| Alarm | Condition | First thing to check |
| --- | --- | --- |
| API errors | Load balancer 5xx above 1% of requests for 5 minutes | Logs Insights "server errors" query |
| API slow | p95 response time above 2 s for 10 minutes | "slowest endpoints" query; database CPU |
| Unhealthy instances | Any target unhealthy for 5 minutes | `/health/ready` reason; ECS task events |
| Service below capacity | Running tasks below desired for 5 minutes | ECS events (crash loop, out of memory) |
| Error log lines | More than 10 `ERROR` lines in 5 minutes | "errors and tracebacks" query |
| Database CPU | Above 80% for 15 minutes | Slow queries (Performance Insights) |
| Database storage | Less than 20% free | Grow storage (autoscaling is on) |
| Database connections | Above 80% of the maximum | Task count, connection leaks |
| Nightly backup | The backup task failed or didn't run | Backup task logs; re-run it by hand |
| Email | SES bounce rate above 5% or complaints above 0.1% | Recent emails; sender reputation |

## Backups

| What | How | Kept | Recovery point |
| --- | --- | --- | --- |
| Database, continuous | RDS automated backups with point-in-time recovery | 14 days | Any second in the window (about 5 minutes behind live) |
| Database, nightly copy | `ops/db-backup.sh` as a scheduled task: `pg_dump` to a separate, versioned, KMS-encrypted S3 bucket | 90 days (then deleted by a lifecycle rule) | Last night |
| Product images | S3 versioning on the media bucket | Deleted versions kept 30 days | Any version |
| Courier files | S3 versioning on the private bucket | Deleted versions kept 30 days | Any version |

Targets: lose at most 5 minutes of orders (RPO), and be back within 1 hour (RTO).

**A backup isn't a backup until it has been restored.**

- Every pull request's CI runs `ops/restore-drill.sh`. It dumps the database the end-to-end tests just
  filled, restores the dump into a scratch database, and checks that every table has the same row count.
- Once a month, restore last night's staging dump into a new database with `ops/db-restore.sh` and
  sign in to the admin portal against it. Write the date and the time it took in the log at the end
  of this page.

## Restoring

Never restore over the live database. Restore into a new database, check it, then point the API at it.

**A. Undo a mistake (bad import, wrong bulk change): point-in-time recovery**

1. Note the time just before the mistake, in UTC. The audit log shows when staff actions happened.
2. Restore to a new instance:
   `aws rds restore-db-instance-to-point-in-time --source-db-instance-identifier <live> --target-db-instance-identifier <live>-restore-<date> --restore-time <UTC time>`
   (or use "Restore to point in time" in the RDS console), with the same subnet group and security group.
3. Either copy only the affected rows back to the live database (safest when the mistake is narrow),
   or put the new instance's address in the `DATABASE_URL` secret and redeploy the API to switch over.
4. Orders placed after the restore time exist only in the old database. Copy them across before
   switching, or switch only during a maintenance pause.

**B. Database lost, or point-in-time recovery unavailable: nightly copy**

1. Create an empty database (a new RDS instance, or `create database` on an existing one).
2. Run `ops/db-restore.sh s3://<backup bucket>/db/<yyyy>/<mm>/<dd>/<file>.dump <new DATABASE_URL>`
   from the backup task image, which has the right `pg_restore` version. The script refuses to
   restore into a database that already has tables.
3. Switch the API's `DATABASE_URL` and redeploy, as in A.

**C. One table:** `pg_restore --data-only --table=<name> --dbname=<scratch DATABASE_URL> <dump>`
into a scratch database, then copy the rows you need.

## Secrets

All secrets live in AWS Secrets Manager and reach the API as environment variables. Never put them
in the repository, task definitions or chat.

| Secret | Rotating it |
| --- | --- |
| `JWT_SECRET` | Set a new value and redeploy. Everyone is signed out once; nothing else is lost. |
| `MFA_ENCRYPTION_KEY` | Set it to `new-key,old-key`, deploy, run `python -m app.cli rotate-mfa-key` as a one-off task, then set it to `new-key` and deploy again. Losing the key means every staff member sets up their app again (`reset-mfa`). |
| Database password | Rotate in Secrets Manager (RDS-managed rotation), then redeploy the API. |

## Staff can't sign in

- **Forgot their password:** "Forgot your password?" on the admin sign-in page, or a Super Admin
  sets a new one on their staff page.
- **Lost their phone:** they can sign in with a recovery code. Otherwise a Super Admin uses "Reset
  two-step sign-in" on their staff page.
- **The only Super Admin lost their phone and their recovery codes:** run
  `python -m app.cli reset-mfa --email <them>` as a one-off API task.
- **"Too many login attempts":** wait 5 minutes. Only failed attempts count, per account and per
  address.

## When something is wrong

1. Check `/health/ready` on the public site (`/api/` is proxied, so use the load balancer address or
   the ECS task directly) and the alarm that fired.
2. Find the failing requests with the Logs Insights queries above, then follow one `request_id`.
3. If a deploy caused it, roll back: redeploy the previous image tag. This works because of a rule
   for every migration: stay backwards compatible for one release (add columns and tables; drop or
   rename them only in a later release), so the previous image runs against the new schema.
4. If data is damaged, follow "Restoring" above. Don't delete anything first.
5. Afterwards, note what happened, how it was found and what will stop it happening again.

## Restore drill log

| Date | Environment | Dump | Time to restore | By | Notes |
| --- | --- | --- | --- | --- | --- |
| 2026-11-15 | Local | `restore-drill.sh` | under 1 minute | Claude | 25 tables, identical row counts |
