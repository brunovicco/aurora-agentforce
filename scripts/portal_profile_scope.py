"""Prepare private profile-only object and field permission review packages."""

import argparse
import copy
import hashlib
import io
import json
import re
import stat
from pathlib import Path, PurePosixPath
from xml.etree.ElementTree import Element, tostring  # nosec B405 - construction only; defused parse
from zipfile import ZipFile

from defusedxml import ElementTree as ET

NS = "{http://soap.sforce.com/2006/04/metadata}"
PROFILE = "Aurora Customer"
KEEP = {"Account", "Contact"}
DENY = {
    "Address",
    "Asset",
    "Case",
    "Contract",
    "Document",
    "Entitlement",
    "EntitlementContact",
    "Idea",
    "Individual",
    "Location",
    "Order",
    "Pricebook2",
    "Product2",
    "ReturnOrder",
    "ServiceAppointment",
    "ServiceResource",
    "ServiceTerritory",
    "Shipment",
    "Solution",
    "WorkOrder",
    "WorkType",
    "WorkTypeGroup",
}
FLAGS = (
    "allowCreate",
    "allowDelete",
    "allowEdit",
    "allowRead",
    "modifyAllRecords",
    "viewAllFields",
    "viewAllRecords",
)
MANIFEST = """<?xml version="1.0" encoding="UTF-8"?>
<Package xmlns="http://soap.sforce.com/2006/04/metadata">
    <types>
        <members>Aurora Customer</members>
        <name>Profile</name>
    </types>
    <version>68.0</version>
</Package>
"""


def parse(data: bytes) -> Element:
    root = ET.parse(
        io.BytesIO(data), forbid_dtd=True, forbid_entities=True, forbid_external=True
    ).getroot()
    if root is None:
        raise ValueError("Missing profile root")
    return root


def read_profile(path: Path, digest: str) -> Element:
    if path.is_symlink() or not path.is_file():
        raise ValueError("Invalid archive")
    if not re.fullmatch(r"[0-9a-f]{64}", digest):
        raise ValueError("Invalid expected digest")
    if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
        raise ValueError("Archive digest mismatch")
    with ZipFile(path) as archive:
        names = set()
        for item in archive.infolist():
            member = PurePosixPath(item.filename)
            if (
                member.is_absolute()
                or ".." in member.parts
                or "\\" in item.filename
                or stat.S_ISLNK(item.external_attr >> 16)
                or item.filename in names
            ):
                raise ValueError("Unsafe archive member")
            names.add(item.filename)
        if archive.testzip() is not None:
            raise ValueError("Archive CRC failure")
        profiles = [n for n in names if n.endswith(f"/profiles/{PROFILE}.profile")]
        if len(profiles) != 1:
            raise ValueError("Expected exactly one target profile")
        if sum(n.endswith(".profile") for n in names) != 1:
            raise ValueError("Unexpected additional profiles")
        root = parse(archive.read(profiles[0]))
    if root.tag != NS + "Profile":
        raise ValueError("Invalid profile root")
    return root


def flags(row: Element, keys: tuple[str, ...]) -> dict[str, str]:
    result = {}
    for key in keys:
        nodes = row.findall(NS + key)
        if len(nodes) != 1 or nodes[0].text not in {"true", "false"}:
            raise ValueError("Missing or invalid permission flag")
        result[key] = str(nodes[0].text)
    return result


def prepare(root: Element) -> tuple[Element, Element, dict[str, object]]:
    """Build minimal restore/candidate payloads; do not modify the source."""
    restore = Element(NS + "Profile")
    candidate = Element(NS + "Profile")
    seen = set()
    outside_fields: dict[str, int] = {}
    changed_fields = 0
    changed_objects = 0
    for row in root.findall(NS + "fieldPermissions"):
        field = row.findtext(NS + "field")
        if field is None or "." not in field or field in seen:
            raise ValueError("Invalid or duplicate field entry")
        seen.add(field)
        obj = field.split(".", 1)[0]
        current = flags(row, ("editable", "readable"))
        if obj not in KEEP | DENY:
            outside_fields[obj] = outside_fields.get(obj, 0) + 1
            continue
        if obj in DENY and "true" in current.values():
            restore.append(copy.deepcopy(row))
            target = copy.deepcopy(row)
            for key in current:
                node = target.find(NS + key)
                if node is None:
                    raise ValueError("Missing permission")
                node.text = "false"
            candidate.append(target)
            changed_fields += 1
    objects = set()
    for row in root.findall(NS + "objectPermissions"):
        object_name = row.findtext(NS + "object")
        if object_name is None or object_name not in KEEP | DENY or object_name in objects:
            raise ValueError("Unexpected or duplicate object entry")
        objects.add(object_name)
        current = flags(row, FLAGS)
        if object_name in KEEP:
            if any(
                value != ("true" if key == "allowRead" else "false")
                for key, value in current.items()
            ):
                raise ValueError("Identity object permissions differ from reviewed baseline")
            continue
        restore.append(copy.deepcopy(row))
        target = copy.deepcopy(row)
        for key in FLAGS:
            node = target.find(NS + key)
            if node is None:
                raise ValueError("Missing permission")
            node.text = "false"
        candidate.append(target)
        changed_objects += 1
    if objects != KEEP | DENY:
        raise ValueError("Object coverage differs from reviewed baseline")
    report: dict[str, object] = {
        "scoped_objects": changed_objects,
        "scoped_fields": changed_fields,
        "preserved_objects": sorted(KEEP),
        "outside_scope_field_counts": dict(sorted(outside_fields.items())),
        "outside_scope_review_required": bool(outside_fields),
        "unverified_objects": [
            "AuroraCaseApproval__c",
            "MessagingEndUser",
            "MessagingSession",
            "User",
            "UserExternalCredential",
        ],
        "effective_permissions_verified": False,
        "deployment_authorized": False,
    }
    return restore, candidate, report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("archive", type=Path)
    parser.add_argument("sha256")
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    output = args.output.resolve()
    if output.is_relative_to(Path(__file__).resolve().parents[1]) or output.exists():
        raise ValueError("Use a new private directory outside the repository")
    restore, candidate, report = prepare(read_profile(args.archive, args.sha256))
    output.mkdir(mode=0o700)
    for label, root in (("restore", restore), ("candidate", candidate)):
        directory = output / label
        profiles = directory / "profiles"
        profiles.mkdir(parents=True)
        (directory / "package.xml").write_text(MANIFEST)
        payload = tostring(root, encoding="utf-8", xml_declaration=True)
        (profiles / f"{PROFILE}.profile").write_bytes(payload)
        report[label + "_sha256"] = hashlib.sha256(payload).hexdigest()
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
