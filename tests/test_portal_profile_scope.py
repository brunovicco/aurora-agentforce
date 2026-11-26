"""Tests for the scoped profile preparation."""

from xml.etree.ElementTree import Element, SubElement

import pytest
from scripts.portal_profile_scope import DENY, FLAGS, KEEP, NS, prepare


def baseline() -> Element:
    root = Element(NS + "Profile")
    for name in sorted(KEEP | DENY):
        row = SubElement(root, NS + "objectPermissions")
        SubElement(row, NS + "object").text = name
        for key in FLAGS:
            SubElement(row, NS + key).text = "true" if key == "allowRead" else "false"
    return root


def test_scope() -> None:
    root = baseline()
    row = SubElement(root, NS + "fieldPermissions")
    SubElement(row, NS + "field").text = "Case.Subject"
    SubElement(row, NS + "editable").text = "true"
    SubElement(row, NS + "readable").text = "true"
    restore, candidate, report = prepare(root)
    assert report["scoped_objects"] == 22
    assert report["scoped_fields"] == 1
    assert report["deployment_authorized"] is False
    assert len(restore) == len(candidate) == 23
    assert all(
        item.findtext(NS + "allowRead") == "false"
        for item in candidate.findall(NS + "objectPermissions")
    )
    assert row.findtext(NS + "editable") == "true"
    assert candidate.findtext(NS + "fieldPermissions/" + NS + "readable") == "false"


def test_missing_object_blocks() -> None:
    root = baseline()
    root.remove(root[0])
    with pytest.raises(ValueError, match="coverage"):
        prepare(root)


def test_outside_scope_fields_are_reported_not_changed() -> None:
    root = baseline()
    row = SubElement(root, NS + "fieldPermissions")
    SubElement(row, NS + "field").text = "AuroraCaseApproval__c.Example__c"
    SubElement(row, NS + "editable").text = "true"
    SubElement(row, NS + "readable").text = "true"
    restore, candidate, report = prepare(root)
    assert report["outside_scope_field_counts"] == {"AuroraCaseApproval__c": 1}
    assert report["outside_scope_review_required"] is True
    assert restore.findall(NS + "fieldPermissions") == []
    assert candidate.findall(NS + "fieldPermissions") == []
    assert row.findtext(NS + "editable") == "true"
    assert report["deployment_authorized"] is False


def test_unexpected_object_still_blocks() -> None:
    root = baseline()
    row = SubElement(root, NS + "objectPermissions")
    SubElement(row, NS + "object").text = "Unexpected__c"
    with pytest.raises(ValueError, match="Unexpected"):
        prepare(root)
