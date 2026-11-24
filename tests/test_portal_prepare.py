"""Regression tests for portal metadata validation."""

import json
import shutil
from pathlib import Path

import pytest
from defusedxml.common import DTDForbidden

from scripts import portal_prepare as portal


@pytest.fixture
def template(tmp_path):
    return Path(shutil.copytree(portal.ROOT, tmp_path / "template"))


def test_valid_template(template):
    portal.validate(template)


@pytest.mark.parametrize(
    ("old", "new"),
    [
        ("<selfRegistration>false", "<selfRegistration>true"),
        ("<enableDirectMessages>false", "<enableDirectMessages>true"),
        ("<status>UnderConstruction", "<status>Live"),
    ],
)
def test_unsafe_network(template, old, new):
    path = template / portal.NETWORK
    content = path.read_text()
    assert old in content
    path.write_text(content.replace(old, new))
    with pytest.raises(ValueError):
        portal.validate(template)


def test_extra_manifest_member(template):
    path = template / "package.xml"
    content = path.read_text()
    path.write_text(content.replace("</types>", "<members>*</members></types>", 1))
    with pytest.raises(ValueError, match="Unexpected manifest"):
        portal.validate(template)


def test_dtd_forbidden(template):
    path = template / portal.NETWORK
    path.write_text("<!DOCTYPE Network><Network/>")
    with pytest.raises(DTDForbidden):
        portal.validate(template)


def test_guest_access(template):
    path = template / portal.BUNDLE / "config/auroraCustomerPortal.json"
    data = json.loads(path.read_text())
    data["isAvailableToGuests"] = True
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="Guest access"):
        portal.validate(template)


def test_broken_route(template):
    path = next((template / portal.BUNDLE / "routes").glob("*.json"))
    data = json.loads(path.read_text())
    data["activeViewId"] = "missing-view"
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="Broken route"):
        portal.validate(template)


def test_symbolic_link(template, tmp_path):
    (template / "link").symlink_to(tmp_path)
    with pytest.raises(ValueError, match="Symbolic links"):
        portal.validate(template)


@pytest.fixture
def rendered(tmp_path, monkeypatch):
    root = tmp_path / "rendered"
    monkeypatch.setattr(
        "sys.argv",
        [
            "portal_prepare.py",
            "--output",
            str(root),
            "--sender",
            "sender@example.com",
            "--admin",
            "admin@example.com",
            "--owner",
            "owner@example.com",
        ],
    )
    portal.main()
    return root


def verify(root):
    portal.verify_rendered(root, "sender@example.com", "admin@example.com", "owner@example.com")


def test_rendered_integrity(rendered):
    verify(rendered)


def test_rendered_tampering(rendered):
    path = rendered / portal.NETWORK
    path.write_text(path.read_text() + "\n")
    with pytest.raises(ValueError, match="Rendered metadata differs"):
        verify(rendered)


def test_rendered_extra_file(rendered):
    (rendered / "extra.xml").write_text("<extra/>")
    with pytest.raises(ValueError, match="Rendered file inventory differs"):
        verify(rendered)
