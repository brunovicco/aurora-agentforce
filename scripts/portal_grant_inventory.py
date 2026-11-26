"""Normalize private Salesforce query results into conservative grant evidence."""

import argparse
import json
from pathlib import Path
from typing import Any

from scripts.portal_customer_inventory import EXPECTED, reconcile
from scripts.portal_permission_review import OBJECTS, review

SYSTEM_FLAGS = ("PermissionsViewAllData", "PermissionsModifyAllData", "PermissionsManageUsers")

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
    sites: list[dict[str, Any]] | None = None,
    field_grants: list[dict[str, Any]] | None = None,
    system_grants: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    if not reconcile(users)["ready"]:
        raise ValueError("Customer reconciliation failed")
    identities = {
        label: next(row for row in users if row["Contact"]["Account"]["Name"] == account)
        for label, (account, _, _) in EXPECTED.items()
    }
    if sites is not None:
        if len(sites) != 1 or sites[0].get("Name") != "Aurora_Customer_Portal":
            raise ValueError("Missing or ambiguous Aurora site")
        guest = sites[0].get("GuestUser")
        if (
            not isinstance(guest, dict)
            or guest.get("UserType") != "Guest"
            or not guest.get("Id")
            or guest["Id"] != sites[0].get("GuestUserId")
            or guest["Id"] in {row["Id"] for row in identities.values()}
        ):
            raise ValueError("Invalid site guest identity")
        identities["guest"] = guest
    actors = {}
    field_findings: set[tuple[str, str, str]] = set()
    system_findings: set[tuple[str, str]] = set()
    gaps: set[str] = set()
    for label, user in identities.items():
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
        if len(owned) != 1:
            gaps.add(f"{label}:profile_source_missing_or_ambiguous")
        if field_grants is None:
            gaps.add(f"{label}:field_inventory_missing")
        else:
            for row in field_grants:
                if row.get("ParentId") not in sources or row.get("SObjectType") not in OBJECTS:
                    continue
                name = row["SObjectType"]
                for flag, key in (("read", "PermissionsRead"), ("edit", "PermissionsEdit")):
                    if not isinstance(row.get(key), bool):
                        raise ValueError("Invalid field permission flag")
                    if row[key]:
                        field_findings.add((label, name, flag))
        if system_grants is None:
            gaps.add(f"{label}:system_inventory_missing")
        else:
            matched = [row for row in system_grants if row.get("Id") in sources]
            if {row["Id"] for row in matched} != sources:
                gaps.add(f"{label}:system_source_missing")
            for row in matched:
                for flag in SYSTEM_FLAGS:
                    if not isinstance(row.get(flag), bool):
                        raise ValueError("Invalid system permission flag")
                    if row[flag]:
                        system_findings.add((label, flag))
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
    if "guest" not in actors:
        actors["guest"] = {
            "groups_present": None,
            "sources_complete": False,
            "object_grants": [],
        }
    return {
        "actors": actors,
        "field_grant_objects": [
            {"actor": actor, "object": name, "grant": flag}
            for actor, name, flag in sorted(field_findings)
        ],
        "observed_broad_system_grants": [
            {"actor": actor, "permission": flag} for actor, flag in sorted(system_findings)
        ],
        "additional_review_gaps": sorted(gaps),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("directory", type=Path)
    args = parser.parse_args()
    evidence = normalize(
        load_rows(args.directory / "users.json"),
        load_rows(args.directory / "profiles.json"),
        load_rows(args.directory / "assignments.json"),
        load_rows(args.directory / "grants.json"),
        load_rows(args.directory / "sites.json"),
        load_rows(args.directory / "fields.json"),
        load_rows(args.directory / "system.json"),
    )
    report = review(evidence)
    for key in ("field_grant_objects", "observed_broad_system_grants", "additional_review_gaps"):
        report[key] = evidence[key]
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
