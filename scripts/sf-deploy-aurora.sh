#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT/salesforce"
ORG="${1:-aurora-dev}"

# Explicit opt-in: never deploy automatically from pull requests or reviews.
if [[ "${AURORA_CONFIRM_DEPLOY:-}" != 'YES' ]]; then
  echo "Deployment blocked. Set AURORA_CONFIRM_DEPLOY=YES explicitly after dry-run review." >&2
  exit 2
fi

sf project deploy start \
  --source-dir force-app \
  --target-org "$ORG" \
  --api-version 68.0 \
  --test-level NoTestRun
