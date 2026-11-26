#!/usr/bin/env bash
set -euo pipefail
[[ $# == 2 ]] || { echo 'Usage: bash scripts/sf-audit-portal-case-probe.sh ORG_ALIAS PROBE_MARKER' >&2; exit 2; }
[[ "$2" =~ ^AURORA-PROBE-[A-F0-9]{16}$ ]] || { echo 'Invalid probe marker' >&2; exit 2; }
root=$(cd "$(dirname "$0")/.." && pwd)
umask 077
private_dir=$(mktemp -d)
trap 'rm -rf -- "$private_dir"' EXIT
cd "$root/salesforce"
sf data query --target-org "$1" --json --query "SELECT Id FROM Case WHERE Subject = '$2'" > "$private_dir/cases.json"
cd "$root"
uv run python - "$private_dir/cases.json" <<'PY'
import json
import sys
from pathlib import Path

from scripts.portal_grant_inventory import load_rows

rows = load_rows(Path(sys.argv[1]))
print(json.dumps({
    "matching_case_count": len(rows),
    "scope": "exact_subject_only",
    "runtime_access_verified": False,
    "mutations": 0,
}, indent=2))
PY
