#!/usr/bin/env bash
set -euo pipefail
[[ $# == 4 ]] || { echo 'Usage: sf-check-portal-postdeploy.sh ORG_ALIAS BACKUP_DIR CANDIDATE_DIR SHA256' >&2; exit 2; }
root=$(cd "$(dirname "$0")/.." && pwd)
umask 077
fresh=$(mktemp -d "${TMPDIR:-/tmp}/aurora-postdeploy.XXXXXX")
trap 'rm -rf -- "$fresh"' EXIT
cd "$root/salesforce"
sf project retrieve start --manifest portal-template/package.xml \
  --target-metadata-dir "$fresh" --api-version 68.0 --target-org "$1" --wait 30
cd "$root"
uv run python scripts/portal_backup.py "$fresh"
uv run python -m scripts.portal_postdeploy "$2" "$fresh" "$3" "$4"
