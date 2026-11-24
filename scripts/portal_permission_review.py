"""Conservative offline review of normalized portal permission evidence."""

import argparse
import json
from pathlib import Path
from typing import Any

OBJECTS = {
    "Account",
    "Contact",
    "User",
    "Case",
    "AuroraCaseApproval__c",
    "Order",
    "MessagingSession",
    "MessagingEndUser",
}
ACTORS = {"customer_a", "customer_b", "guest"}
FLAGS = {"read", "create", "update", "delete", "view_all", "modify_all"}
IDENTITY_OBJECTS = {"Account", "Contact", "User"}


def review(evidence: dict[str, Any]) -> dict[str, Any]:
    """Report observed grants and gaps; never infer effective access denial."""
    findings: set[tuple[str, str, str]] = set()
    gaps: set[str] = set()
    actors = evidence.get("actors")
    if not isinstance(actors, dict) or set(actors) != ACTORS:
        raise ValueError("Exactly three synthetic actor labels required")
    for actor, data in actors.items():
        if not isinstance(data, dict):
            raise ValueError("Invalid actor evidence")
        if data.get("groups_present") is not False:
            gaps.add(f"{actor}:group_resolution_required")
        if data.get("sources_complete") is not True:
            gaps.add(f"{actor}:source_inventory_incomplete")
        grants = data.get("object_grants")
        if not isinstance(grants, list):
            raise ValueError("Invalid object grants")
        for row in grants:
            if not isinstance(row, dict) or row.get("object") not in OBJECTS:
                raise ValueError("Invalid object grant row")
            name = row["object"]
            if set(row) != FLAGS | {"object"}:
                raise ValueError("Incomplete or unexpected grant flags")
            for flag in FLAGS:
                if not isinstance(row[flag], bool):
                    raise ValueError("Grant flags must be boolean")
                if not row[flag]:
                    continue
                if flag == "read" and name in IDENTITY_OBJECTS and actor != "guest":
                    gaps.add(f"{actor}:{name}:field_and_record_scope_required")
                else:
                    findings.add((actor, name, flag))
    return {
        "observed_disallowed_grants": [
            {"actor": actor, "object": name, "grant": flag}
            for actor, name, flag in sorted(findings)
        ],
        "review_gaps": sorted(gaps),
        "status": "review_required" if findings or gaps else "no_conflict_in_supplied_rows",
        "effective_permissions_verified": False,
        "runtime_access_verified": False,
        "mutations": 0,
    }


def main() -> None:
    """Read normalized evidence; output only synthetic actor and object labels."""
    parser = argparse.ArgumentParser()
    parser.add_argument("evidence", type=Path)
    args = parser.parse_args()
    report = review(json.loads(args.evidence.read_text()))
    print(json.dumps(report, indent=2))
    if report["status"] == "review_required":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
