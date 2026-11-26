#!/usr/bin/env bash
set -euo pipefail
[[ $# == 2 ]] || { echo 'Usage: sf-validate-portal-restore.sh ORG_ALIAS BACKUP_DIR' >&2; exit 2; }
root=$(cd "$(dirname "$0")/.." && pwd)
cd "$root"
archive=$(uv run python scripts/portal_backup.py --verify "$2")
cd "$root/salesforce"
sf project deploy start --dry-run --metadata-dir "$archive" --target-org "$1" --wait 30
echo "Restore dry-run complete; no restoration performed."
