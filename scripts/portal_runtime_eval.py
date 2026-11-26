"""Score manually observed portal evidence without claiming independent verification."""

import argparse
import json
import re
from pathlib import Path
from typing import Any

SCENARIOS = Path(__file__).resolve().parents[1] / "evals/portal-runtime-scenarios.json"
OUTCOMES = {"denied", "identity_matched", "own_read_only", "unexpected", "not_run"}


def evaluate(plan: dict[str, Any], evidence: dict[str, Any]) -> dict[str, Any]:
    """Reject malformed evidence and calculate deterministic scenario outcomes."""
    if evidence.get("schema_version") != 1:
        raise ValueError("Unsupported evidence schema")
    if evidence.get("environment") != "isolated_development":
        raise ValueError("Isolated development environment required")
    commit = evidence.get("candidate_commit")
    if not isinstance(commit, str) or not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise ValueError("Full candidate commit required")
    expected = {case["id"]: case["expected"] for case in plan["cases"]}
    rows = evidence.get("observations")
    if not isinstance(rows, list):
        raise ValueError("Missing observations")
    seen = set()
    results = []
    for row in rows:
        if not isinstance(row, dict) or set(row) != {
            "id",
            "observed",
            "data_disclosed",
            "mutations",
            "evidence_ref",
        }:
            raise ValueError("Invalid observation")
        case_id = row["id"]
        if case_id not in expected or case_id in seen:
            raise ValueError("Unknown or duplicate scenario")
        seen.add(case_id)
        observed = row["observed"]
        if observed not in OUTCOMES:
            raise ValueError("Invalid observed outcome")
        if observed == "not_run":
            if any(row[key] is not None for key in ("data_disclosed", "mutations", "evidence_ref")):
                raise ValueError("Unexecuted scenario contains evidence")
            status = "not_run"
        else:
            reference = row["evidence_ref"]
            if not isinstance(reference, str) or not re.fullmatch(r"EV-[0-9]{3,6}", reference):
                raise ValueError("Sanitized evidence reference required")
            if not isinstance(row["data_disclosed"], bool):
                raise ValueError("Disclosure flag required")
            if type(row["mutations"]) is not int or row["mutations"] < 0:
                raise ValueError("Mutation count required")
            status = (
                "pass"
                if observed == expected[case_id]
                and row["data_disclosed"] is False
                and row["mutations"] == 0
                else "fail"
            )
        results.append({"id": case_id, "status": status})
    for missing in sorted(set(expected) - seen):
        results.append({"id": missing, "status": "not_run"})
    counts = {
        status: sum(row["status"] == status for row in results)
        for status in ("pass", "fail", "not_run")
    }
    return {
        "candidate_commit": commit,
        "counts": counts,
        "results": sorted(results, key=lambda row: row["id"]),
        "all_reported_checks_pass": counts["pass"] == len(expected),
        "independently_verified": False,
        "activation_authorized": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("evidence", type=Path)
    args = parser.parse_args()
    report = evaluate(json.loads(SCENARIOS.read_text()), json.loads(args.evidence.read_text()))
    print(json.dumps(report, indent=2))
    if not report["all_reported_checks_pass"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
