"""Compare the candidate ExperienceBundle to a retained private metadata backup."""

import argparse
import json
import unicodedata
from pathlib import Path
from zipfile import ZipFile

from scripts.portal_backup import verify_backup
from scripts.portal_prepare import BUNDLE, ROOT

APPROVED = {
    "views/início.json",
    "themes/atendimentoAoCliente.json",
    "brandingSets/customerService.json",
}


def canonical(name: str) -> str:
    return unicodedata.normalize("NFC", name)


def comparable(name: str, raw: bytes) -> object:
    return json.loads(raw) if name.endswith(".json") else raw


def compare(archive_path: Path, candidate: Path) -> dict[str, object]:
    before: dict[str, object] = {}
    after: dict[str, object] = {}
    with ZipFile(archive_path) as archive:
        manifest = next(name for name in archive.namelist() if name.endswith("package.xml"))
        prefix = manifest.removesuffix("package.xml") + BUNDLE.as_posix() + "/"
        for entry in archive.infolist():
            if entry.is_dir() or not entry.filename.startswith(prefix):
                continue
            name = canonical(entry.filename.removeprefix(prefix))
            if name in before:
                raise ValueError("Backup filename normalization collision")
            before[name] = comparable(name, archive.read(entry))
    for path in candidate.rglob("*"):
        if path.is_symlink():
            raise ValueError("Candidate symbolic link")
        if path.is_file():
            name = canonical(path.relative_to(candidate).as_posix())
            if name in after:
                raise ValueError("Candidate filename normalization collision")
            after[name] = comparable(name, path.read_bytes())
    if not before or not after:
        raise ValueError("Missing experience bundle")
    added = set(after) - set(before)
    removed = set(before) - set(after)
    changed = {name for name in before.keys() & after.keys() if before[name] != after[name]}
    return {
        "backup_file_count": len(before),
        "candidate_file_count": len(after),
        "approved_changed_files": sorted(changed & APPROVED),
        "unexpected_changed_count": len(changed - APPROVED),
        "added_count": len(added),
        "removed_count": len(removed),
        "scope_matches": not added and not removed and changed == APPROVED,
        "live_drift_verified": False,
        "deployment_authorized": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("backup", type=Path)
    args = parser.parse_args()
    report = compare(verify_backup(args.backup), ROOT / BUNDLE)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    if not report["scope_matches"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
