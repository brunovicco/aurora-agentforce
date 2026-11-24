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
        (x.findtext(NS + "name"), x.findtext(NS + "members")) for x in package.findall(NS + "types")
    ]
    require(
        actual
        == [
            ("CustomSite", "Aurora_Customer_Portal"),
            ("ExperienceBundle", "Aurora_Customer_Portal1"),
            ("Network", "Aurora Customer Portal"),
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


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    parser.add_argument("--sender")
    parser.add_argument("--admin")
    parser.add_argument("--owner")
    args = parser.parse_args()
    validate(ROOT)
    if args.output is None:
        return
    values = [args.sender, args.admin, args.owner]
    require(
        all(
            v and re.fullmatch(r"[A-Za-z0-9._+%-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", v) for v in values
        ),
        "Valid sender, admin and owner required",
    )
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
    print("Rendered private metadata directory; no deployment performed.")


if __name__ == "__main__":
    main()
