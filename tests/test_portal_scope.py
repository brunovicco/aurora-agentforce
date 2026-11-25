"""Tests for drift comparison and scoped package digests."""

from pathlib import Path
from zipfile import ZipFile

from scripts.portal_scope import package_digest, payload


def test_json_semantic_comparison(tmp_path: Path) -> None:
    first = tmp_path / "first.zip"
    second = tmp_path / "second.zip"
    for path, value in ((first, '{"a":1,"b":2}'), (second, '{"b":2, "a":1}')):
        with ZipFile(path, "w") as archive:
            archive.writestr("unpackaged/package.xml", "")
            archive.writestr("unpackaged/experience.json", value)
    assert payload(first) == payload(second)
    with ZipFile(second, "w") as archive:
        archive.writestr("unpackaged/package.xml", "")
        archive.writestr("unpackaged/experience.json", '{"a":2}')
    assert payload(first) != payload(second)


def test_digest_changes_with_contents(tmp_path: Path) -> None:
    path = tmp_path / "package.xml"
    path.write_text("first")
    before = package_digest(tmp_path)
    path.write_text("second")
    assert package_digest(tmp_path) != before
