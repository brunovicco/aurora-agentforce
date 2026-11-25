#!/usr/bin/env bash
set -euo pipefail
[[ $# == 1 ]] || { echo 'Usage: sf-backup-portal.sh ORG_ALIAS' >&2; exit 2; }
root=$(cd "$(dirname "$0")/.." && pwd)
umask 077
backup=$(mktemp -d "${TMPDIR:-/tmp}/aurora-backup.XXXXXX")
echo "Private backup directory: $backup"
cd "$root/salesforce"
sf project retrieve start --manifest portal-template/package.xml \
  --target-metadata-dir "$backup" --api-version 68.0 --target-org "$1" --wait 30
cd "$root"
uv run python scripts/portal_backup.py "$backup"
echo "Backup captured. No deployment performed. Keep this directory private."
