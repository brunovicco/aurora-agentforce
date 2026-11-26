"""Tests for a sanitized comparison of portal candidate and backup."""

from pathlib import Path
from zipfile import ZipFile

from scripts.portal_compare import APPROVED, compare
from scripts.portal_prepare import BUNDLE


def make_pair(tmp_path: Path) -> tuple[Path, Path]:
    archive_path = tmp_path / "backup.zip"
    candidate = tmp_path / "candidate"
    with ZipFile(archive_path, "w") as archive:
        archive.writestr("unpackaged/package.xml", "")
        for name in APPROVED | {"config/unchanged.json"}:
            archive.writestr(f"unpackaged/{BUNDLE.as_posix()}/{name}", '{"value": 1}')
            path = candidate / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text('{"value": 2}' if name in APPROVED else '{ "value": 1 }')
    return archive_path, candidate


def test_expected_scope(tmp_path: Path) -> None:
    archive, candidate = make_pair(tmp_path)
    result = compare(archive, candidate)
    assert result["scope_matches"] is True
    assert result["deployment_authorized"] is False
    assert result["approved_changed_files"] == sorted(APPROVED)


def test_unexpected_changes_block_scope(tmp_path: Path) -> None:
    archive, candidate = make_pair(tmp_path)
    (candidate / "config/unchanged.json").write_text('{"value": 3}')
    result = compare(archive, candidate)
    assert result["scope_matches"] is False
    assert result["unexpected_changed_count"] == 1


def test_added_file_blocks_scope(tmp_path: Path) -> None:
    archive, candidate = make_pair(tmp_path)
    (candidate / "extra.json").write_text("{}")
    assert compare(archive, candidate)["scope_matches"] is False
