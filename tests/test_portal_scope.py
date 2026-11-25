"""Tests for drift comparison and scoped package digests."""

from pathlib import Path
from zipfile import ZipFile

from scripts.portal_prepare import BUNDLE, ROOT
from scripts.portal_scope import DESCRIPTOR, MANIFEST, build_package, package_digest, payload


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


def test_scoped_package_includes_descriptor(tmp_path: Path) -> None:
    output = tmp_path / "metadata"
    build_package(ROOT, output)
    assert (output / DESCRIPTOR).read_bytes() == (ROOT / DESCRIPTOR).read_bytes()
    assert (output / "package.xml").read_text() == MANIFEST
    expected = {p.relative_to(ROOT) for p in (ROOT / BUNDLE).rglob("*") if p.is_file()}
    actual = {p.relative_to(output) for p in output.rglob("*") if p.is_file()}
    assert actual == expected | {DESCRIPTOR, Path("package.xml")}
