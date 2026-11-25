"""Compare retrieved post-deployment metadata with the exact approved scope."""

import argparse
import json
from copy import deepcopy
from pathlib import Path
from typing import Any

from scripts.portal_backup import verify_backup
from scripts.portal_compare import canonical, comparable
from scripts.portal_prepare import BUNDLE
from scripts.portal_scope import payload, verify_candidate


EMPTY_REGION_PATHS = {
    f"{BUNDLE.as_posix()}/themes/atendimentoAoCliente.json": (
        ("views", 1, "regions", 1),
    ),
    f"{BUNDLE.as_posix()}/views/início.json": tuple(("regions", i) for i in range(1, 5)),
}


def region_at(document: Any, path: tuple[str | int, ...]) -> Any:
    """Resolve a fixed structural path without modifying the document."""
    for part in path:
        if isinstance(part, str) and isinstance(document, dict) and part in document:
            document = document[part]
        elif isinstance(part, int) and isinstance(document, list) and part < len(document):
            document = document[part]
        else:
            return None
    return document


def reconcile_empty_regions(
    name: str, expected: Any, actual: Any
) -> tuple[Any, list[str]]:
    """Reconcile only the observed omission of explicitly empty region arrays."""
    normalized = deepcopy(actual)
    omissions = []
    for path in EMPTY_REGION_PATHS.get(name, ()):
        before = region_at(expected, path)
        after = region_at(normalized, path)
        if (
            isinstance(before, dict)
            and isinstance(after, dict)
            and before.get("type") == after.get("type") == "region"
            and isinstance(before.get("id"), str)
            and before.get("id") == after.get("id")
            and before.get("regionName") == after.get("regionName")
            and before.get("components") == []
            and "components" not in after
        ):
            after["components"] = []
            omissions.append("$/" + "/".join(map(str, path)) + "/components")
    return normalized, omissions


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
    raw_mismatched = mismatched.copy()
    diagnostics = []
    omissions = []
    for name in sorted(raw_mismatched):
        normalized, paths = reconcile_empty_regions(name, expected[name], actual[name])
        if paths:
            omissions.append({"file": name, "paths": paths})
        if name in approved and normalized == expected[name]:
            mismatched.remove(name)
            continue
        changes = differences(expected[name], normalized if name in approved else actual[name])
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
        "raw_mismatch_count": len(raw_mismatched),
        "empty_region_omissions": omissions,
        "strict_metadata_matches": not added and not missing and not raw_mismatched,
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
