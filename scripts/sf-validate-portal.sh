#!/usr/bin/env bash
set -euo pipefail
[[ $# == 2 ]] || { echo 'Usage: sf-validate-portal.sh ORG_ALIAS PRIVATE_METADATA_DIR' >&2; exit 2; }
root=$(cd "$(dirname "$0")/.." && pwd)
python3 "$root/scripts/portal_prepare.py"
[[ -f "$2/package.xml" ]] || exit 2
cd "$root/salesforce"
sf project deploy start --dry-run --metadata-dir "$2" --target-org "$1" --wait 30
