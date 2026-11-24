#!/usr/bin/env bash
set -euo pipefail
[[ $# == 1 ]] || { echo 'Usage: sf-audit-portal-customers.sh ORG_ALIAS' >&2; exit 2; }
root=$(cd "$(dirname "$0")/.." && pwd)
umask 077
private_dir=$(mktemp -d)
trap 'rm -rf -- "$private_dir"' EXIT
cd "$root/salesforce"
sf data query --target-org "$1" --json --query "SELECT Id, ContactId, IsActive, IsPortalEnabled, Profile.Name, Contact.FirstName, Contact.LastName, Contact.AccountId, Contact.Account.Name FROM User WHERE Contact.Account.Name IN ('Aurora Demo Account A', 'Aurora Demo Account B')" > "$private_dir/users.json"
cd "$root"
uv run python scripts/portal_customer_inventory.py "$private_dir/users.json"
