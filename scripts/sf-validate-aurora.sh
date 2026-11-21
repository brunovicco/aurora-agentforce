#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT/salesforce"
ORG="${1:-aurora-dev}"

if ! find force-app -type f ! -name '.gitkeep' -print -quit | grep -q .; then
  echo "No Salesforce metadata retrieved yet. Run scripts/sf-retrieve-aurora.sh first." >&2
  exit 1
fi

# Validate against a Developer Edition without changing org state.
# The existing draft Flow may not deploy until the implementation is complete.
sf project deploy start \
  --source-dir force-app \
  --target-org "$ORG" \
  --api-version 68.0 \
  --dry-run \
  --test-level NoTestRun
