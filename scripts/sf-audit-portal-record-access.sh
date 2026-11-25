#!/usr/bin/env bash
set -euo pipefail
[[ $# == 1 ]] || { echo 'Usage: sf-audit-portal-record-access.sh ORG_ALIAS' >&2; exit 2; }
root=$(cd "$(dirname "$0")/.." && pwd)
umask 077
private_dir=$(mktemp -d)
trap 'rm -rf -- "$private_dir"' EXIT
cd "$root/salesforce"
sf data query --target-org "$1" --json --query "SELECT Id, ContactId, IsActive, IsPortalEnabled, Profile.Name, Contact.FirstName, Contact.LastName, Contact.AccountId, Contact.Account.Name FROM User WHERE Contact.Account.Name IN ('Aurora Demo Account A', 'Aurora Demo Account B')" > "$private_dir/users.json"
cd "$root"
uv run python - "$private_dir" > "$private_dir/ids.tsv" <<'PY'
import re
import sys
from pathlib import Path
from scripts.portal_customer_inventory import EXPECTED, reconcile
from scripts.portal_grant_inventory import load_rows

rows = load_rows(Path(sys.argv[1]) / "users.json")
if not reconcile(rows)["ready"]:
    raise SystemExit("Customer reconciliation failed")
for label, (account, _, _) in EXPECTED.items():
    row = next(r for r in rows if r["Contact"]["Account"]["Name"] == account)
    ids = (row["Id"], row["Contact"]["AccountId"])
    if not all(re.fullmatch(r"[A-Za-z0-9]{15}(?:[A-Za-z0-9]{3})?", v) for v in ids):
        raise SystemExit("Invalid Salesforce record ID")
    print(label, *ids, sep="\t")
PY
accounts=$(awk -F '\t' '{printf "%s\047%s\047", NR==1?"":",",$3}' "$private_dir/ids.tsv")
cd "$root/salesforce"
while IFS=$'\t' read -r actor user_id account_id; do
  sf data query --target-org "$1" --json --query "SELECT RecordId, HasReadAccess, HasEditAccess FROM UserRecordAccess WHERE UserId = '$user_id' AND RecordId IN ($accounts)" > "$private_dir/$actor.json"
done < "$private_dir/ids.tsv"
cd "$root"
uv run python -m scripts.portal_record_access "$private_dir"
