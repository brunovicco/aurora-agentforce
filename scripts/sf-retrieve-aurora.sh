#!/usr/bin/env bash
set -euo pipefail

# Run from any directory. No deploy, commit, or push is performed.
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT/salesforce"
ORG="${1:-aurora-dev}"
AGENT="${AURORA_AGENT_API_NAME:-Aurora_Pos_Venda}"

if ! command -v sf >/dev/null 2>&1; then
  echo "Salesforce CLI not installed. Install/update it before retrieving." >&2
  exit 1
fi

echo "Retrieving metadata from Salesforce org alias: $ORG"
echo "Agent API name: $AGENT"
echo "Using API 68.0. Both CLI and org must support Winter '27 metadata types."

# Retrieve published definition/version plus direct dependencies, including
# the Agent Script source authoring bundle. Limit: 25 dependency retrieves/day.
sf project retrieve start \
  --metadata "AiAgentDefinitionVersion:${AGENT}#*" \
  --root-type-with-dependencies AiAgentDefinitionVersion \
  --target-org "$ORG" \
  --api-version 68.0

# This is the org-created schema, integration registration and permission set.
# Do not synthesize these XML files: use Salesforce as initial ground truth.
sf project retrieve start \
  --manifest manifest/aurora-base.xml \
  --target-org "$ORG" \
  --api-version 68.0

echo "Retrieve completed. Review all files in salesforce/force-app."
echo "No Named/External Credential metadata or secret values were retrieved by this script."
echo "Do not commit generated compiled agentScript copies if present; keep the source .agent."
