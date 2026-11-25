"""Synthetic tests for read-only portal identity reconciliation."""

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest
from scripts.portal_customer_inventory import main, reconcile


def records() -> list[dict[str, Any]]:
    return [
        {
            "Id": f"user-{label}",
            "ContactId": f"contact-{label}",
            "IsActive": True,
            "IsPortalEnabled": True,
            "Profile": {"Name": "Aurora Customer"},
            "Contact": {
                "FirstName": name,
                "LastName": "Demo",
                "AccountId": f"account-{label}",
                "Account": {"Name": f"Aurora Demo Account {label}"},
            },
        }
        for label, name in (("A", "Alice"), ("B", "Bob"))
    ]


def test_reconcile_existing_customers() -> None:
    report = reconcile(records())
    assert report["ready"] is True
    assert report["mutations"] == 0
    assert report["runtime_access_verified"] is False
    assert report["customers"] == {"customer_a": "matched", "customer_b": "matched"}


def test_missing_customer() -> None:
    assert reconcile(records()[:1])["ready"] is False


def test_duplicate_customer() -> None:
    rows = records()
    rows.append(deepcopy(rows[0]))
    assert reconcile(rows)["customers"]["customer_a"] == "missing_or_ambiguous"


def test_inactive_customer() -> None:
    rows = records()
    rows[0]["IsActive"] = False
    assert reconcile(rows)["ready"] is False


def test_shared_account() -> None:
    rows = records()
    rows[1]["Contact"]["AccountId"] = rows[0]["Contact"]["AccountId"]
    assert reconcile(rows)["customers"]["customer_b"] == "shared_identity"


def test_wrong_profile() -> None:
    rows = records()
    rows[0]["Profile"]["Name"] = "System Administrator"
    assert reconcile(rows)["ready"] is False


@pytest.mark.parametrize("mode", ["success", "missing", "failed", "truncated", "not_done"])
def test_cli(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mode: str) -> None:
    rows = records() if mode != "missing" else records()[:1]
    payload = {
        "status": 1 if mode == "failed" else 0,
        "result": {
            "done": mode != "not_done",
            "totalSize": len(rows) + (mode == "truncated"),
            "records": rows,
        },
    }
    path = tmp_path / "inventory.json"
    path.write_text(json.dumps(payload))
    monkeypatch.setattr("sys.argv", ["inventory", str(path)])
    if mode == "success":
        main()
    else:
        with pytest.raises(SystemExit):
            main()
