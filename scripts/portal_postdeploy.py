"""Compare retrieved post-deployment metadata with the exact approved scope."""

import argparse
import json
from pathlib import Path

from scripts.portal_backup import verify_backup
from scripts.portal_compare import canonical, comparable
from scripts.portal_scope import payload, verify_candidate


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
    mismatched = {name for name in expected.keys() & actual.keys() if expected[name] != actual[name]}
    return {
        "expected_file_count": len(expected),
        "retrieved_file_count": len(actual),
        "added_count": len(added),
        "missing_count": len(missing),
        "candidate_mismatch_count": len(mismatched & approved.keys()),
        "outside_scope_mismatch_count": len(mismatched - approved.keys()),
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
