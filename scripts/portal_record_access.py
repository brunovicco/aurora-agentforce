"""Review administrator-observed record access for synthetic customer accounts."""

import argparse
import json
from pathlib import Path
from typing import Any

from scripts.portal_customer_inventory import EXPECTED, reconcile
from scripts.portal_grant_inventory import load_rows


def inspect_access(
    users: list[dict[str, Any]], evidence: dict[str, list[dict[str, Any]]]
) -> dict[str, Any]:
    if not reconcile(users)["ready"]:
        raise ValueError("Customer reconciliation failed")
    accounts = {
        label: next(
            row["Contact"]["AccountId"]
            for row in users
            if row["Contact"]["Account"]["Name"] == account
        )
        for label, (account, _, _) in EXPECTED.items()
    }
    results = []
    for actor, rows in sorted(evidence.items()):
        if actor not in accounts:
            raise ValueError("Unexpected actor")
        for target, record_id in sorted(accounts.items()):
            matches = [row for row in rows if row.get("RecordId") == record_id]
            if len(matches) != 1:
                outcome = "unknown"
            else:
                row = matches[0]
                flags = [row.get(key) for key in ("HasReadAccess", "HasEditAccess")]
                if not all(isinstance(flag, bool) for flag in flags):
                    raise ValueError("Invalid record access flags")
                if flags[1] or (actor != target and flags[0]):
                    outcome = "review_required"
                elif flags[0]:
                    outcome = "own_read_observed"
                else:
                    outcome = "no_read_or_edit_observed"
            results.append({"actor": actor, "target": target, "outcome": outcome})
    return {
        "account_access": results,
        "complete": set(evidence) == set(accounts)
        and all(row["outcome"] != "unknown" for row in results),
        "runtime_access_verified": False,
        "mutations": 0,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("directory", type=Path)
    args = parser.parse_args()
    users = load_rows(args.directory / "users.json")
    evidence = {actor: load_rows(args.directory / f"{actor}.json") for actor in EXPECTED}
    print(json.dumps(inspect_access(users, evidence), indent=2))


if __name__ == "__main__":
    main()
