#!/usr/bin/env bash
# Logical backup of the database to S3, on top of the automatic RDS snapshots and point-in-time
# recovery. Runs nightly as a scheduled task in AWS (see docs/operations.md).
#
#   DATABASE_URL   postgresql://user:pass@host:5432/dbname (libpq form, no "+psycopg"), or the
#                  standard PGHOST, PGUSER, PGPASSWORD, PGDATABASE (and PGSSLMODE) variables
#   BACKUP_BUCKET  S3 bucket for dumps (versioned, encrypted, with a lifecycle rule)
#   BACKUP_PREFIX  optional, default "db"
set -euo pipefail

if [ -z "${DATABASE_URL:-}" ] && [ -z "${PGHOST:-}" ]; then
  echo "Set DATABASE_URL, or PGHOST and the other PG* variables" >&2
  exit 1
fi
: "${BACKUP_BUCKET:?set BACKUP_BUCKET}"
prefix="${BACKUP_PREFIX:-db}"
stamp="$(date -u +%Y%m%dT%H%M%SZ)"
key="${prefix}/$(date -u +%Y/%m/%d)/ecommerce-${stamp}.dump"

echo "Backing up to s3://${BACKUP_BUCKET}/${key}"
# Custom format: compressed, and pg_restore can restore single tables from it.
pg_dump --format=custom --no-owner --no-acl ${DATABASE_URL:+--dbname="${DATABASE_URL}"} \
  | aws s3 cp - "s3://${BACKUP_BUCKET}/${key}" --sse aws:kms --only-show-errors
size="$(aws s3api head-object --bucket "${BACKUP_BUCKET}" --key "${key}" --query ContentLength)"
if [ "${size}" -lt 1024 ]; then
  echo "Backup is suspiciously small (${size} bytes)" >&2
  exit 1
fi
echo "Backup done: ${size} bytes"
