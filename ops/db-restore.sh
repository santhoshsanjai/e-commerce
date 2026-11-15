#!/usr/bin/env bash
# Restore a logical backup into an EMPTY database. Never point this at the live database: restore
# into a new one, check it, then switch the API's DATABASE_URL over (see docs/operations.md).
#
#   ops/db-restore.sh <dump file or s3://bucket/key> <target DATABASE_URL>
set -euo pipefail

source_dump="${1:?usage: db-restore.sh <dump file or s3://...> <target DATABASE_URL>}"
target="${2:?usage: db-restore.sh <dump file or s3://...> <target DATABASE_URL>}"

tables="$(psql "${target}" -Atc "select count(*) from information_schema.tables where table_schema = 'public'")"
if [ "${tables}" != "0" ]; then
  echo "Refusing: the target database already has ${tables} tables. Restore into an empty one." >&2
  exit 1
fi

if [[ "${source_dump}" == s3://* ]]; then
  local_dump="$(mktemp)"
  trap 'rm -f "${local_dump}"' EXIT
  aws s3 cp "${source_dump}" "${local_dump}" --only-show-errors
  source_dump="${local_dump}"
fi

pg_restore --no-owner --no-acl --exit-on-error --dbname="${target}" "${source_dump}"
echo "Restored. Schema version: $(psql "${target}" -Atc 'select version_num from alembic_version')"
