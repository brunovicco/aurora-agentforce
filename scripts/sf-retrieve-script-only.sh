#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT/salesforce"
ORG="${1:-aurora-dev}"
AGENT="${AURORA_AGENT_API_NAME:-Aurora_Pos_Venda}"
# Useful if the agent has only a draft authoring bundle or the v68 version
# retrieve cannot see the current draft. Check the actual bundle API name.
sf project retrieve start \
  --metadata "AiAuthoringBundle:${AGENT}*" \
  --target-org "$ORG" \
  --api-version 68.0
