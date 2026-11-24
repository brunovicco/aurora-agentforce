#!/usr/bin/env bash
set -euo pipefail
[[ $# == 2 ]] || { echo 'Usage: sf-validate-portal.sh ORG_ALIAS PRIVATE_METADATA_DIR' >&2; exit 2; }
root=$(cd "$(dirname "$0")/.." && pwd)
cd "$root"
: "${PORTAL_SENDER:?Set PORTAL_SENDER}"
: "${PORTAL_ADMIN:?Set PORTAL_ADMIN}"
: "${PORTAL_OWNER:?Set PORTAL_OWNER}"
uv run python scripts/portal_prepare.py --verify-rendered "$2" \
  --sender "$PORTAL_SENDER" --admin "$PORTAL_ADMIN" --owner "$PORTAL_OWNER"
metadata_dir=$(cd "$2" && pwd -P)
cd "$root/salesforce"
sf project deploy start --dry-run --metadata-dir "$metadata_dir" --target-org "$1" --wait 30
