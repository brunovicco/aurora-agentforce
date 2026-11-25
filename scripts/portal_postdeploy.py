"""Compare retrieved post-deployment metadata with the exact approved scope."""

import argparse
import json
from pathlib import Path
from typing import Any

from scripts.portal_backup import verify_backup
from scripts.portal_compare import canonical, comparable
from scripts.portal_scope import payload, verify_candidate


def differences(expected: Any, actual: Any, path: str = "$") -> list[dict[str, str]]:
    """Report structural paths and categories, never metadata values."""
    if type(expected) is not type(actual):
        return [{"path": path, "kind": "type_changed"}]
    if isinstance(expected, dict):
        result: list[dict[str, str]] = []
        for key in sorted(expected.keys() | actual.keys()):
            child = f"{path}/{key.replace('~', '~0').replace('/', '~1')}"
            if key not in actual:
                result.append({"path": child, "kind": "missing_property"})
            elif key not in expected:
                result.append({"path": child, "kind": "added_property"})
            else:
                result.extend(differences(expected[key], actual[key], child))
        return result
    if isinstance(expected, list):
        result = []
        if len(expected) != len(actual):
            result.append({"path": path, "kind": "array_length_changed"})
        for index, (left, right) in enumerate(zip(expected, actual, strict=False)):
            result.extend(differences(left, right, f"{path}/{index}"))
        return result
    if expected != actual:
        return [{"path": path, "kind": "value_changed"}]
    return []


def assess(
    original: dict[str, object],
    actual: dict[str, object],
    approved: dict[str, object],
) -> dict[str, object]:
    if not approved or not set(approved).issubset(original):
        raise ValueError("Unexpected candidate inventory")
    expected = original | approved
    added = set(actual) - set(expected)
    missing = set(expected) - set(actual)
    mismatched = {
        name for name in expected.keys() & actual.keys() if expected[name] != actual[name]
    }
    diagnostics = []
    for name in sorted(mismatched):
        changes = differences(expected[name], actual[name])
        diagnostics.append(
            {
                "file": name,
                "difference_count": len(changes),
                "differences": changes[:50],
                "truncated": len(changes) > 50,
            }
        )
    return {
        "expected_file_count": len(expected),
        "retrieved_file_count": len(actual),
        "added_count": len(added),
        "missing_count": len(missing),
        "candidate_mismatch_count": len(mismatched & approved.keys()),
        "outside_scope_mismatch_count": len(mismatched - approved.keys()),
        "mismatch_diagnostics": diagnostics,
        "metadata_matches": not added and not missing and not mismatched,
        "publication_verified": False,
        "runtime_access_verified": False,
        "mutations": 0,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("original", type=Path)
    parser.add_argument("fresh", type=Path)
    parser.add_argument("candidate", type=Path)
    parser.add_argument("sha256")
    args = parser.parse_args()
    verify_candidate(args.candidate, args.sha256)
    approved = {
        canonical(path.relative_to(args.candidate).as_posix()): comparable(
            path.name, path.read_bytes()
        )
        for path in args.candidate.rglob("*")
        if path.is_file() and path.relative_to(args.candidate) != Path("package.xml")
    }
    report = assess(
        payload(verify_backup(args.original)), payload(verify_backup(args.fresh)), approved
    )
    print(json.dumps(report, indent=2))
    if not report["metadata_matches"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
