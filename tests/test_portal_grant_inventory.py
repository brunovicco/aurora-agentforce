"""Synthetic tests for normalized Salesforce grant collection."""

import json
from pathlib import Path
from typing import Any

import pytest
from scripts.portal_grant_inventory import FIELDS, load_rows, main, normalize
from scripts.portal_permission_review import review


def users() -> list[dict[str, Any]]:
    return [
        {
            "Id": f"user-{label}",
            "ProfileId": "profile",
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


def test_profile_and_direct_grants() -> None:
    profiles = [{"Id": "profile-set", "ProfileId": "profile", "IsOwnedByProfile": True}]
    assignments = [
        {"AssigneeId": "user-A", "PermissionSetId": "direct", "PermissionSetGroupId": "group"}
    ]
    grants = [
        {
            "ParentId": parent,
            "SObjectType": "Case",
            **{field: field == "PermissionsCreate" for field in FIELDS.values()},
        }
        for parent in ("profile-set", "direct", "unrelated")
    ]
    evidence = normalize(users(), profiles, assignments, grants)
    assert len(evidence["actors"]["customer_a"]["object_grants"]) == 2
    assert len(evidence["actors"]["customer_b"]["object_grants"]) == 1
    assert evidence["actors"]["customer_a"]["groups_present"] is True
    report = review(evidence)
    assert len(report["observed_disallowed_grants"]) == 2
    assert report["effective_permissions_verified"] is False
    assert "guest:source_inventory_incomplete" in report["review_gaps"]


def test_missing_identity_rejected() -> None:
    with pytest.raises(ValueError, match="reconciliation"):
        normalize(users()[:1], [], [], [])


def test_missing_profile_rejected() -> None:
    rows = users()
    del rows[0]["ProfileId"]
    with pytest.raises(ValueError, match="profile"):
        normalize(rows, [], [], [])


@pytest.mark.parametrize("complete", [True, False])
def test_load_rows(tmp_path: Path, complete: bool) -> None:
    path = tmp_path / "query.json"
    path.write_text(
        json.dumps({"status": 0, "result": {"done": complete, "totalSize": 0, "records": []}})
    )
    if complete:
        assert load_rows(path) == []
    else:
        with pytest.raises(ValueError, match="Incomplete"):
            load_rows(path)


def site() -> dict[str, Any]:
    return {
        "Name": "Aurora_Customer_Portal",
        "GuestUserId": "guest-user",
        "GuestUser": {"Id": "guest-user", "ProfileId": "guest-profile", "UserType": "Guest"},
    }


def test_guest_grant_collected() -> None:
    profiles = [{"Id": "guest-set", "ProfileId": "guest-profile", "IsOwnedByProfile": True}]
    grants = [
        {
            "ParentId": "guest-set",
            "SObjectType": "Account",
            **{field: field == "PermissionsRead" for field in FIELDS.values()},
        }
    ]
    report = review(normalize(users(), profiles, [], grants, [site()]))
    assert report["observed_disallowed_grants"] == [
        {"actor": "guest", "object": "Account", "grant": "read"}
    ]


@pytest.mark.parametrize("mode", ["missing", "duplicate", "wrong_site", "wrong_user"])
def test_invalid_site(mode: str) -> None:
    sites = [site()]
    if mode == "missing":
        sites = []
    elif mode == "duplicate":
        sites.append(site())
    elif mode == "wrong_site":
        sites[0]["Name"] = "Other"
    else:
        sites[0]["GuestUser"]["UserType"] = "Standard"
    with pytest.raises(ValueError):
        normalize(users(), [], [], [], sites)


def test_cli(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    for name, rows in (
        ("users", users()),
        ("profiles", []),
        ("assignments", []),
        ("grants", []),
        ("sites", [site()]),
    ):
        payload = {"status": 0, "result": {"done": True, "totalSize": len(rows), "records": rows}}
        (tmp_path / f"{name}.json").write_text(json.dumps(payload))
    monkeypatch.setattr("sys.argv", ["inventory", str(tmp_path)])
    main()
