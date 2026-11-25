"""Check the original Metadata API ZIP without extracting or altering it."""

import argparse
import hashlib
import io
import json
import stat
from pathlib import Path, PurePosixPath
from zipfile import ZipFile

from defusedxml import ElementTree as ET

NS = "{http://soap.sforce.com/2006/04/metadata}"
MEMBERS = {
    "CustomSite": ["Aurora_Customer_Portal"],
    "ExperienceBundle": ["Aurora_Customer_Portal1"],
    "Network": ["Aurora Customer Portal"],
}


def inspect_archive(path: Path) -> dict[str, object]:
    """Reject missing components, unsafe paths and malformed manifests."""
    if path.is_symlink() or not path.is_file():
        raise ValueError("Invalid archive path")
    with ZipFile(path) as archive:
        names = set()
        for entry in archive.infolist():
            name = PurePosixPath(entry.filename)
            if (
                name.is_absolute()
                or ".." in name.parts
                or "\\" in entry.filename
                or stat.S_ISLNK(entry.external_attr >> 16)
                or entry.filename in names
            ):
                raise ValueError("Unsafe ZIP member")
            names.add(entry.filename)
        if archive.testzip() is not None:
            raise ValueError("Archive CRC failure")
        manifests = [name for name in names if PurePosixPath(name).name == "package.xml"]
        if len(manifests) != 1:
            raise ValueError("Expected exactly one package manifest")
        manifest = manifests[0]
        prefix = manifest.removesuffix("package.xml")
        root = ET.parse(
            io.BytesIO(archive.read(manifest)),
            forbid_dtd=True,
            forbid_entities=True,
            forbid_external=True,
        ).getroot()
        if root is None:
            raise ValueError("Missing manifest root")
        types = root.findall(NS + "types")
        actual = {
            node.findtext(NS + "name"): [member.text for member in node.findall(NS + "members")]
            for node in types
        }
        if actual != MEMBERS or len(types) != len(MEMBERS):
            raise ValueError("Unexpected backup manifest")
        if root.findtext(NS + "version") != "68.0":
            raise ValueError("Unexpected API version")
        required = (
            "sites/Aurora_Customer_Portal.site",
            "networks/Aurora Customer Portal.network",
        )
        # ExperienceBundle descriptor extensions vary; check the bundle directory separately.
        if not all(prefix + name in names for name in required):
            raise ValueError("Missing site or network metadata")
        bundle = prefix + "experiences/Aurora_Customer_Portal1/"
        if not any(
            name.startswith(bundle + "routes/") and name.endswith(".json") for name in names
        ):
            raise ValueError("Missing experience routes")
        if not any(name.startswith(bundle + "views/") and name.endswith(".json") for name in names):
            raise ValueError("Missing experience views")
    return {
        "archive": path.name,
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "components": sorted(MEMBERS),
        "archive_integrity_verified": True,
        "restore_validated": False,
    }


def verify_backup(directory: Path) -> Path:
    """Check the retained archive against the original integrity report."""
    directory = directory.resolve()
    if directory.is_relative_to(Path(__file__).resolve().parents[1]):
        raise ValueError("Backup must remain outside repository")
    report = json.loads((directory / "backup-integrity.json").read_text())
    archives = list(directory.glob("*.zip"))
    if len(archives) != 1 or inspect_archive(archives[0]) != report:
        raise ValueError("Backup integrity report mismatch")
    return archives[0]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("directory", type=Path)
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    if args.verify:
        print(verify_backup(args.directory))
        return
    directory = args.directory.resolve()
    repo = Path(__file__).resolve().parents[1]
    if directory.is_relative_to(repo):
        raise ValueError("Backup must remain outside repository")
    archives = list(directory.glob("*.zip"))
    if len(archives) != 1:
        raise ValueError("Expected exactly one retrieved ZIP")
    report = inspect_archive(archives[0])
    output = directory / "backup-integrity.json"
    with output.open("x") as handle:
        json.dump(report, handle, indent=2)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
