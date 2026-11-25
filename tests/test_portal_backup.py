"""Tests for private metadata archive checks."""

import json
from pathlib import Path
from zipfile import ZipFile

import pytest
from scripts.portal_backup import inspect_archive, verify_backup
from scripts.portal_prepare import ROOT


def make_zip(path: Path, *, unsafe: bool = False, omit_site: bool = False) -> None:
    with ZipFile(path, "w") as archive:
        for file in ROOT.rglob("*"):
            if file.is_file():
                if omit_site and file.suffix == ".site":
                    continue
                archive.write(file, "unpackaged/" + file.relative_to(ROOT).as_posix())
        if unsafe:
            archive.writestr("../outside", "test")


def test_valid_backup(tmp_path: Path) -> None:
    path = tmp_path / "backup.zip"
    make_zip(path)
    report = inspect_archive(path)
    assert report["archive_integrity_verified"] is True
    assert report["restore_validated"] is False


@pytest.mark.parametrize("mode", ["unsafe", "missing_site"])
def test_invalid_backup(tmp_path: Path, mode: str) -> None:
    path = tmp_path / "backup.zip"
    make_zip(path, unsafe=mode == "unsafe", omit_site=mode == "missing_site")
    with pytest.raises(ValueError):
        inspect_archive(path)


def test_verify_retained_backup(tmp_path: Path) -> None:
    path = tmp_path / "backup.zip"
    make_zip(path)
    report = inspect_archive(path)
    (tmp_path / "backup-integrity.json").write_text(json.dumps(report))
    assert verify_backup(tmp_path) == path
    report["sha256"] = "0" * 64
    (tmp_path / "backup-integrity.json").write_text(json.dumps(report))
    with pytest.raises(ValueError, match="mismatch"):
        verify_backup(tmp_path)
