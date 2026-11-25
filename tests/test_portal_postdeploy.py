"""Tests for post-deployment metadata scope verification."""

from copy import deepcopy

import pytest
from scripts.portal_postdeploy import EMPTY_REGION_PATHS, assess, differences


def test_matching_candidate_and_preserved_scope() -> None:
    result = assess({"bundle": 1, "network": 2}, {"bundle": 3, "network": 2}, {"bundle": 3})
    assert result["metadata_matches"] is True
    assert result["publication_verified"] is False
    assert result["runtime_access_verified"] is False


@pytest.mark.parametrize(
    ("actual", "field"),
    [
        ({"bundle": 1, "network": 2}, "candidate_mismatch_count"),
        ({"bundle": 3, "network": 9}, "outside_scope_mismatch_count"),
        ({"bundle": 3}, "missing_count"),
        ({"bundle": 3, "network": 2, "extra": 1}, "added_count"),
    ],
)
def test_unexpected_metadata(actual: dict[str, object], field: str) -> None:
    result = assess({"bundle": 1, "network": 2}, actual, {"bundle": 3})
    assert result["metadata_matches"] is False
    assert result[field] == 1


def test_invalid_scope() -> None:
    with pytest.raises(ValueError, match="inventory"):
        assess({"bundle": 1}, {"bundle": 1}, {"unknown": 3})


def test_diagnostics_do_not_return_values() -> None:
    changes = differences(
        {"component": {"label": "private-before", "items": [1, 2], "gone": True}},
        {"component": {"label": "private-after", "items": [1], "new": False}},
    )
    assert {"path": "$/component/label", "kind": "value_changed"} in changes
    assert {"path": "$/component/items", "kind": "array_length_changed"} in changes
    assert {"path": "$/component/gone", "kind": "missing_property"} in changes
    assert {"path": "$/component/new", "kind": "added_property"} in changes
    assert "private-before" not in str(changes)
    assert "private-after" not in str(changes)


def test_mismatch_diagnostic_keeps_gate_closed() -> None:
    result = assess({"bundle": 1}, {"bundle": 2}, {"bundle": 3})
    assert result["metadata_matches"] is False
    assert result["mismatch_diagnostics"] == [
        {
            "file": "bundle",
            "difference_count": 1,
            "differences": [{"path": "$", "kind": "value_changed"}],
            "truncated": False,
        }
    ]


def test_observed_empty_region_omission() -> None:
    name = next(name for name in EMPTY_REGION_PATHS if name.endswith("início.json"))
    region: dict[str, object] = {"type": "region", "id": "synthetic", "regionName": "featured", "components": []}
    candidate: dict[str, list[dict[str, object]]] = {"regions": [{}, region]}
    actual = deepcopy(candidate)
    del actual["regions"][1]["components"]
    result = assess({name: candidate}, {name: actual}, {name: candidate})
    assert result["strict_metadata_matches"] is False
    assert result["metadata_matches"] is True
    assert result["raw_mismatch_count"] == 1
    assert result["empty_region_omissions"] == [
        {"file": name, "paths": ["$/regions/1/components"]}
    ]
    assert "components" not in actual["regions"][1]


@pytest.mark.parametrize("mode", ["nonempty", "wrong_id", "other_path", "null", "other_file"])
def test_empty_region_exception_is_narrow(mode: str) -> None:
    name = next(name for name in EMPTY_REGION_PATHS if name.endswith("início.json"))
    region: dict[str, object] = {"type": "region", "id": "synthetic", "regionName": "featured", "components": []}
    candidate: dict[str, list[dict[str, object]]] = {"regions": [{}, region]}
    if mode == "nonempty":
        region["components"] = [{"type": "component"}]
    if mode == "other_path":
        candidate["regions"] = [{}, {}, {}, {}, {}, region]
    index = len(candidate["regions"]) - 1
    actual = deepcopy(candidate)
    del actual["regions"][index]["components"]
    if mode == "wrong_id":
        actual["regions"][index]["id"] = "other"
    if mode == "null":
        actual["regions"][index]["components"] = None
    if mode == "other_file":
        name = "other.json"
    assert assess({name: candidate}, {name: actual}, {name: candidate})["metadata_matches"] is False
