"""Normalize private Salesforce query results into conservative grant evidence."""

import argparse
import json
from pathlib import Path
from typing import Any

from scripts.portal_customer_inventory import EXPECTED, reconcile
from scripts.portal_permission_review import OBJECTS, review

FIELDS = {
    "read": "PermissionsRead",
    "create": "PermissionsCreate",
    "update": "PermissionsEdit",
    "delete": "PermissionsDelete",
    "view_all": "PermissionsViewAllRecords",
    "modify_all": "PermissionsModifyAllRecords",
}


def load_rows(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text())
    result = payload.get("result", {})
    records = result.get("records")
    if (
        payload.get("status") != 0
        or result.get("done") is not True
        or not isinstance(records, list)
        or result.get("totalSize") != len(records)
        or not all(isinstance(row, dict) for row in records)
    ):
        raise ValueError("Incomplete query evidence")
    return records


def normalize(
    users: list[dict[str, Any]],
    profile_sets: list[dict[str, Any]],
    assignments: list[dict[str, Any]],
    grants: list[dict[str, Any]],
) -> dict[str, Any]:
    if not reconcile(users)["ready"]:
        raise ValueError("Customer reconciliation failed")
    actors = {}
    for label, (account, _, _) in EXPECTED.items():
        user = next(row for row in users if row["Contact"]["Account"]["Name"] == account)
        profile_id = user.get("ProfileId")
        if not isinstance(profile_id, str) or not profile_id:
            raise ValueError("Missing profile identity")
        owned = [
            row["Id"]
            for row in profile_sets
            if row.get("ProfileId") == profile_id and row.get("IsOwnedByProfile") is True
        ]
        assigned = [row for row in assignments if row.get("AssigneeId") == user["Id"]]
        groups_present = any(row.get("PermissionSetGroupId") for row in assigned)
        sources = set(owned) | {
            row["PermissionSetId"] for row in assigned if row.get("PermissionSetId")
        }
        object_grants = []
        for row in grants:
            if row.get("ParentId") not in sources or row.get("SObjectType") not in OBJECTS:
                continue
            object_grants.append(
                {
                    "object": row["SObjectType"],
                    **{flag: row[field] for flag, field in FIELDS.items()},
                }
            )
        actors[label] = {
            "groups_present": groups_present,
            "sources_complete": False,
            "object_grants": object_grants,
        }
    actors["guest"] = {
        "groups_present": None,
        "sources_complete": False,
        "object_grants": [],
    }
    return {"actors": actors}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("directory", type=Path)
    args = parser.parse_args()
    evidence = normalize(
        load_rows(args.directory / "users.json"),
        load_rows(args.directory / "profiles.json"),
        load_rows(args.directory / "assignments.json"),
        load_rows(args.directory / "grants.json"),
    )
    print(json.dumps(review(evidence), indent=2))


if __name__ == "__main__":
    main()
