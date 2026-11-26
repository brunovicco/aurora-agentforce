"""Prepare a narrowly scoped portal package after checking live metadata drift."""

import argparse
import hashlib
import json
import shutil
from pathlib import Path
from zipfile import ZipFile

from scripts.portal_backup import verify_backup
from scripts.portal_compare import canonical, comparable, compare
from scripts.portal_prepare import BUNDLE, ROOT, validate

DESCRIPTOR = BUNDLE.with_suffix(".site-meta.xml")

MANIFEST = """<?xml version="1.0" encoding="UTF-8"?>
<Package xmlns="http://soap.sforce.com/2006/04/metadata">
    <types>
        <members>Aurora_Customer_Portal1</members>
        <name>ExperienceBundle</name>
    </types>
    <version>68.0</version>
</Package>
"""


def payload(path: Path) -> dict[str, object]:
    result: dict[str, object] = {}
    with ZipFile(path) as archive:
        manifest = next(name for name in archive.namelist() if name.endswith("package.xml"))
        prefix = manifest.removesuffix("package.xml")
        for entry in archive.infolist():
            if entry.is_dir() or entry.filename == manifest:
                continue
            if not entry.filename.startswith(prefix):
                raise ValueError("Unexpected archive layout")
            name = canonical(entry.filename.removeprefix(prefix))
            if name in result:
                raise ValueError("Archive filename normalization collision")
            result[name] = comparable(name, archive.read(entry))
    return result


def package_digest(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise ValueError("Package symbolic link")
        if path.is_file():
            name = canonical(path.relative_to(root).as_posix()).encode()
            raw = path.read_bytes()
            digest.update(len(name).to_bytes(8, "big"))
            digest.update(name)
            digest.update(len(raw).to_bytes(8, "big"))
            digest.update(raw)
    return digest.hexdigest()


def build_package(template: Path, output: Path) -> None:
    """Copy the complete ExperienceBundle, including its sibling descriptor."""
    output.mkdir(mode=0o700)
    shutil.copytree(template / BUNDLE, output / BUNDLE)
    shutil.copyfile(template / DESCRIPTOR, output / DESCRIPTOR)
    (output / "package.xml").write_text(MANIFEST)


def prepare(original: Path, fresh: Path, output: Path) -> dict[str, object]:
    original_zip = verify_backup(original)
    fresh_zip = verify_backup(fresh)
    original_payload = payload(original_zip)
    if original_payload != payload(fresh_zip):
        raise ValueError("Live metadata differs from retained backup; stop")
    validate(ROOT)
    report = compare(original_zip, ROOT / BUNDLE)
    if not report["scope_matches"]:
        raise ValueError("Candidate scope mismatch")
    if output.exists() or output.resolve().is_relative_to(ROOT.parents[1]):
        raise ValueError("Output must be new and outside repository")
    if original_payload.get(DESCRIPTOR.as_posix()) != (ROOT / DESCRIPTOR).read_bytes():
        raise ValueError("ExperienceBundle descriptor differs from backup")
    build_package(ROOT, output)
    return {
        "live_drift_verified": True,
        "scope_matches": True,
        "components": ["ExperienceBundle"],
        "package_sha256": package_digest(output),
        "deployment_authorized": False,
    }


def verify_candidate(candidate: Path, expected_digest: str) -> None:
    """Ensure an approved package contains only the exact repository candidate."""
    if not candidate.is_dir() or candidate.is_symlink():
        raise ValueError("Invalid candidate directory")
    if candidate.resolve().is_relative_to(ROOT.parents[1]):
        raise ValueError("Candidate must remain outside repository")
    expected = {
        path.relative_to(ROOT): path.read_bytes()
        for path in (ROOT / BUNDLE).rglob("*")
        if path.is_file()
    }
    expected[DESCRIPTOR] = (ROOT / DESCRIPTOR).read_bytes()
    expected[Path("package.xml")] = MANIFEST.encode()
    actual = {}
    for path in candidate.rglob("*"):
        if path.is_symlink():
            raise ValueError("Candidate symbolic link")
        if path.is_file():
            actual[path.relative_to(candidate)] = path.read_bytes()
    if actual != expected or package_digest(candidate) != expected_digest:
        raise ValueError("Approved candidate inventory or digest mismatch")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("original", type=Path)
    parser.add_argument("fresh", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    print(json.dumps(prepare(args.original, args.fresh, args.output), indent=2))


if __name__ == "__main__":
    main()
