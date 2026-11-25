#!/usr/bin/env bash
set -euo pipefail
[[ $# == 4 ]] || { echo 'Usage: sf-check-portal-deploy.sh ORG_ALIAS BACKUP_DIR CANDIDATE_DIR SHA256' >&2; exit 2; }
root=$(cd "$(dirname "$0")/.." && pwd)
umask 077
fresh=$(mktemp -d "${TMPDIR:-/tmp}/aurora-preflight.XXXXXX")
trap 'rm -rf -- "$fresh"' EXIT
cd "$root/salesforce"
sf project retrieve start --manifest portal-template/package.xml \
  --target-metadata-dir "$fresh" --api-version 68.0 --target-org "$1" --wait 30
cd "$root"
uv run python scripts/portal_backup.py "$fresh"
uv run python - "$2" "$fresh" "$3" "$4" <<'PY'
import sys
from pathlib import Path
from scripts.portal_backup import verify_backup
from scripts.portal_scope import payload, verify_candidate

original, fresh, candidate = map(Path, sys.argv[1:4])
if payload(verify_backup(original)) != payload(verify_backup(fresh)):
    raise SystemExit("Live metadata drift detected; stop")
verify_candidate(candidate, sys.argv[4])
print("Approved candidate integrity and live drift checks passed.")
print("No deployment performed; separate deployment approval required.")
PY
