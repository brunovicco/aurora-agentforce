"""Validate the Aurora portal template and render a private Metadata API directory."""

import argparse
import json
import re
import shutil
from pathlib import Path

from defusedxml import ElementTree as ET

NS = "{http://soap.sforce.com/2006/04/metadata}"
ROOT = Path(__file__).resolve().parents[1] / "salesforce" / "portal-template"
NETWORK = Path("networks/Aurora Customer Portal.network")
SITE = Path("sites/Aurora_Customer_Portal.site")
BUNDLE = Path("experiences/Aurora_Customer_Portal1")


def require(ok: bool, message: str) -> None:
    if not ok:
        raise ValueError(message)


def validate(root: Path) -> None:
    require(not root.is_symlink(), "Symbolic link root")
    require(all(not p.is_symlink() for p in root.rglob("*")), "Symbolic links forbidden")
    network = ET.parse(
        root / NETWORK, forbid_dtd=True, forbid_entities=True, forbid_external=True
    ).getroot()
    site = ET.parse(
        root / SITE, forbid_dtd=True, forbid_entities=True, forbid_external=True
    ).getroot()
    for key in (
        "selfRegistration",
        "enableGuestChatter",
        "enableGuestFileAccess",
        "enableGuestMemberVisibility",
        "enableMemberVisibility",
        "enableDirectMessages",
        "allowInternalUserLogin",
        "sendWelcomeEmail",
    ):
        require(network.findtext(NS + key) == "false", f"Unsafe network setting: {key}")
    require(network.findtext(NS + "status") == "UnderConstruction", "Network must not be live")
    require(site.findtext(NS + "active") == "true", "CustomSite must be active")
    for key in ("browserXssProtection", "contentSniffingProtection"):
        require(site.findtext(NS + key) == "true", f"Missing site protection: {key}")
    groups = network.find(NS + "networkMemberGroups")
    require(
        groups is not None
        and sorted((x.tag, x.text) for x in groups)
        == [(NS + "profile", "admin"), (NS + "profile", "aurora customer")],
        "Unexpected member grants",
    )
    bundle = root / BUNDLE
    docs = {p: json.loads(p.read_text()) for p in bundle.rglob("*.json")}
    config = docs[bundle / "config/auroraCustomerPortal.json"]
    require(config["isAvailableToGuests"] is False, "Guest access enabled")
    for name in ("mainAppPage.json",):
        page = docs[bundle / "config" / name]
        require(
            page["isLockerServiceEnabled"] is True and page["isRelaxedCSPLevel"] is False,
            "Unsafe app security",
        )
    views = [d["id"] for p, d in docs.items() if p.parent.name == "views"]
    routes = [d for p, d in docs.items() if p.parent.name == "routes"]
    require(bool(routes) and len(views) == len(set(views)), "Invalid views")
    require(all(d["activeViewId"] in views for d in routes), "Broken route reference")
    package = ET.parse(
        root / "package.xml", forbid_dtd=True, forbid_entities=True, forbid_external=True
    ).getroot()
    actual = [
        (x.findtext(NS + "name"), [m.text for m in x.findall(NS + "members")])
        for x in package.findall(NS + "types")
    ]
    require(
        actual
        == [
            ("CustomSite", ["Aurora_Customer_Portal"]),
            ("ExperienceBundle", ["Aurora_Customer_Portal1"]),
            ("Network", ["Aurora Customer Portal"]),
        ],
        "Unexpected manifest",
    )
    for p in root.rglob("*"):
        if p.is_file():
            text = p.read_text()
            require(
                not re.search(
                    r"[\w.+-]+@[\w.-]+\.[a-zA-Z]{2,}|\b(?:00D|005|003|001|00e)[a-zA-Z0-9]{12,15}\b",
                    text,
                ),
                f"Environment reference in {p.name}",
            )
    print(f"Validated {len(docs)} JSON files, {len(routes)} routes and metadata controls.")


def verify_rendered(root: Path, sender: str, admin: str, owner: str) -> None:
    validate(ROOT)
    require(root.is_dir() and not root.is_symlink(), "Invalid rendered directory")
    require(not root.resolve().is_relative_to(ROOT.parents[1]), "Output inside repository")
    require(all(not p.is_symlink() for p in root.rglob("*")), "Symbolic links forbidden")
    expected = {p.relative_to(ROOT) for p in ROOT.rglob("*") if p.is_file()}
    actual = {p.relative_to(root) for p in root.rglob("*") if p.is_file()}
    require(actual == expected, "Rendered file inventory differs")
    substitutions = {
        NETWORK: {"__AURORA_SENDER__": sender},
        SITE: {"__AURORA_ADMIN__": admin, "__AURORA_OWNER__": owner},
    }
    for path in expected:
        original = (ROOT / path).read_bytes()
        for token, value in substitutions.get(path, {}).items():
            require(original.count(token.encode()) == 1, "Invalid placeholder count")
            original = original.replace(token.encode(), value.encode())
        require((root / path).read_bytes() == original, "Rendered metadata differs")
    print("Rendered metadata integrity verified.")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    parser.add_argument("--verify-rendered", type=Path)
    parser.add_argument("--sender")
    parser.add_argument("--admin")
    parser.add_argument("--owner")
    args = parser.parse_args()
    validate(ROOT)
    require(not (args.output and args.verify_rendered), "Choose one operation")
    if args.output is None and args.verify_rendered is None:
        return
    values = [args.sender, args.admin, args.owner]
    require(
        all(
            v and re.fullmatch(r"[A-Za-z0-9._+%-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", v) for v in values
        ),
        "Valid sender, admin and owner required",
    )
    if args.verify_rendered is not None:
        verify_rendered(args.verify_rendered, args.sender, args.admin, args.owner)
        return
    require(not args.output.exists(), "Output must not exist")
    require(
        not args.output.resolve().is_relative_to(ROOT.parents[1]),
        "Output must be outside repository",
    )
    shutil.copytree(ROOT, args.output)
    for path, substitutions in [
        (NETWORK, {"__AURORA_SENDER__": args.sender}),
        (SITE, {"__AURORA_ADMIN__": args.admin, "__AURORA_OWNER__": args.owner}),
    ]:
        target = args.output / path
        content = target.read_text()
        for token, value in substitutions.items():
            content = content.replace(token, value)
        target.write_text(content)
    verify_rendered(args.output, args.sender, args.admin, args.owner)
    print("Rendered private metadata directory; no deployment performed.")


if __name__ == "__main__":
    main()
