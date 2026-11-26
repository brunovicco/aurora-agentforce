#!/usr/bin/env bash
# Check-only deployment to an explicitly selected development org.
set -euo pipefail

if [[ $# -ne 1 || -z "${1:-}" || "$1" == -* ]]; then
  echo "Usage: bash scripts/sf-validate-verified-reads.sh <development-org-alias>" >&2
  exit 2
fi

if ! command -v sf >/dev/null 2>&1; then
  echo "Salesforce CLI is required." >&2
  exit 2
fi

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$root/salesforce"

# No org display, login, deploy quick, permission assignment or agent activation.
# The operator must independently confirm that the alias is a development org.
sf project deploy start \
  --dry-run \
  --manifest manifest/aurora-verified-client.xml \
  --target-org "$1" \
  --test-level RunSpecifiedTests \
  --tests AuroraVerifiedOrdersClientTest \
  --tests AuroraTrustedContextTest \
  --tests AuroraBrokerBindingResolverTest \
  --tests AuroraVerifiedReadFacadeTest \
  --tests AuroraAuthenticatedReadRuntimeTest \
  --wait 30
