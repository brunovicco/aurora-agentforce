"""Tests for post-deployment metadata scope verification."""

import pytest
from scripts.portal_postdeploy import assess, differences


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
