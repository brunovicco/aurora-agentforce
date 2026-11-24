"""Synthetic tests for normalized Salesforce grant collection."""

import json
from pathlib import Path
from typing import Any

import pytest
from scripts.portal_grant_inventory import FIELDS, load_rows, normalize
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
