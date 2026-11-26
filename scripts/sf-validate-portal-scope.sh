#!/usr/bin/env bash
set -euo pipefail
[[ $# == 2 ]] || { echo 'Usage: sf-validate-portal-scope.sh ORG_ALIAS BACKUP_DIR' >&2; exit 2; }
root=$(cd "$(dirname "$0")/.." && pwd)
umask 077
fresh=$(mktemp -d "${TMPDIR:-/tmp}/aurora-drift.XXXXXX")
trap 'rm -rf -- "$fresh"' EXIT
work=$(mktemp -d "${TMPDIR:-/tmp}/aurora-scope.XXXXXX")
cd "$root/salesforce"
sf project retrieve start --manifest portal-template/package.xml \
  --target-metadata-dir "$fresh" --api-version 68.0 --target-org "$1" --wait 30
cd "$root"
uv run python scripts/portal_backup.py "$fresh"
uv run python -m scripts.portal_scope "$2" "$fresh" "$work/metadata"
cd "$root/salesforce"
sf project deploy start --dry-run --metadata-dir "$work/metadata" --target-org "$1" --wait 30
echo "Scoped dry-run complete; no deployment performed."
echo "Private candidate directory: $work/metadata"
