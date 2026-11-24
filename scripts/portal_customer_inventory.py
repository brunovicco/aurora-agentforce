"""Read-only reconciliation of synthetic Salesforce portal customer records."""

import argparse
import json
from pathlib import Path
from typing import Any

EXPECTED = {
    "customer_a": ("Aurora Demo Account A", "Alice", "Demo"),
    "customer_b": ("Aurora Demo Account B", "Bob", "Demo"),
}


def reconcile(records: list[dict[str, Any]]) -> dict[str, Any]:
    """Validate exact synthetic identities without exposing record identifiers."""
    results = {}
    account_ids = set()
    contact_ids = set()
    user_ids = set()
    for label, (account, first, last) in EXPECTED.items():
        matches = [
            row
            for row in records
            if row.get("Contact")
            and row["Contact"].get("Account")
            and row["Contact"]["Account"].get("Name") == account
        ]
        if len(matches) != 1:
            results[label] = "missing_or_ambiguous"
            continue
        row = matches[0]
        contact = row["Contact"]
        account_id = contact.get("AccountId")
        contact_id = row.get("ContactId")
        user_id = row.get("Id")
        if (
            contact.get("FirstName") != first
            or contact.get("LastName") != last
            or row.get("IsActive") is not True
            or row.get("IsPortalEnabled") is not True
            or row.get("Profile", {}).get("Name") != "Aurora Customer"
            or not all(isinstance(v, str) and v for v in (account_id, contact_id, user_id))
        ):
            results[label] = "identity_or_status_mismatch"
            continue
        if account_id in account_ids or contact_id in contact_ids or user_id in user_ids:
            results[label] = "shared_identity"
            continue
        account_ids.add(account_id)
        contact_ids.add(contact_id)
        user_ids.add(user_id)
        results[label] = "matched"
    return {
        "customers": results,
        "ready": all(value == "matched" for value in results.values()),
        "runtime_access_verified": False,
        "mutations": 0,
    }


def main() -> None:
    """Consume private Salesforce CLI JSON and report only synthetic labels."""
    parser = argparse.ArgumentParser()
    parser.add_argument("inventory", type=Path)
    args = parser.parse_args()
    payload = json.loads(args.inventory.read_text())
    if payload.get("status") != 0 or payload["result"].get("done") is not True:
        raise SystemExit("Incomplete or failed Salesforce query")
    records = payload["result"]["records"]
    if payload["result"].get("totalSize") != len(records):
        raise SystemExit("Incomplete Salesforce query inventory")
    report = reconcile(records)
    print(json.dumps(report, indent=2))
    if not report["ready"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
