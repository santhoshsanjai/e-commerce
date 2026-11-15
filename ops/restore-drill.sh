#!/usr/bin/env bash
# Backup-and-restore drill against the local Docker Compose database: dump it, restore the dump
# into a scratch database, and check every table came back with the same number of rows.
# Run it monthly against staging too (docs/operations.md); a backup you haven't restored isn't one.
set -euo pipefail

cd "$(dirname "$0")/.."
db() { docker compose exec -T db "$@"; }
drill=restore_drill

echo "1/4 Dumping the ecommerce database"
db pg_dump -U postgres --format=custom --no-owner --no-acl ecommerce > /tmp/restore-drill.dump

echo "2/4 Restoring into a scratch database"
db psql -U postgres -qc "drop database if exists ${drill}" -c "create database ${drill}"
db pg_restore -U postgres --no-owner --no-acl --exit-on-error -d "${drill}" < /tmp/restore-drill.dump

echo "3/4 Comparing row counts"
count_rows='select string_agg(t || '"'"'='"'"' || n, '"'"' '"'"' order by t) from (
  select table_name as t,
    (xpath('"'"'/row/c/text()'"'"', query_to_xml(format('"'"'select count(*) as c from %I'"'"', table_name), false, true, '"'"''"'"')))[1]::text::int as n
  from information_schema.tables where table_schema = '"'"'public'"'"' and table_type = '"'"'BASE TABLE'"'"') x'
original="$(db psql -U postgres -d ecommerce -Atc "${count_rows}")"
restored="$(db psql -U postgres -d "${drill}" -Atc "${count_rows}")"
db psql -U postgres -qc "drop database ${drill}"
rm -f /tmp/restore-drill.dump

echo "4/4 Result"
if [ "${original}" != "${restored}" ]; then
  echo "MISMATCH"; echo "original: ${original}"; echo "restored: ${restored}"; exit 1
fi
echo "OK: $(echo "${original}" | wc -w) tables restored with identical row counts"
echo "${original}" | tr ' ' '\n' | grep -E '^(users|orders|order_items|products|audit_logs|alembic_version)='
