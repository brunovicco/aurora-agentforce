"""Regression tests for the conservative permission evidence reviewer."""

from typing import Any

import pytest
from scripts.portal_permission_review import review


def evidence() -> dict[str, Any]:
    return {
        "actors": {
            actor: {
                "groups_present": False,
                "sources_complete": True,
                "object_grants": [],
            }
            for actor in ("customer_a", "customer_b", "guest")
        }
    }


def grant(name: str, **flags: bool) -> dict[str, Any]:
    return {
        "object": name,
        "read": False,
        "create": False,
        "update": False,
        "delete": False,
        "view_all": False,
        "modify_all": False,
        **flags,
    }


def test_no_grants_is_not_proof_of_denial() -> None:
    result = review(evidence())
    assert result["status"] == "no_conflict_in_supplied_rows"
    assert result["effective_permissions_verified"] is False
    assert result["runtime_access_verified"] is False


@pytest.mark.parametrize("flag", ["read", "create", "update", "delete", "view_all", "modify_all"])
def test_case_grant_requires_review(flag: str) -> None:
    data = evidence()
    data["actors"]["customer_a"]["object_grants"] = [grant("Case", **{flag: True})]
    assert review(data)["observed_disallowed_grants"] == [
        {"actor": "customer_a", "object": "Case", "grant": flag}
    ]


def test_group_requires_resolution() -> None:
    data = evidence()
    data["actors"]["customer_b"]["groups_present"] = True
    assert "customer_b:group_resolution_required" in review(data)["review_gaps"]


def test_identity_read_requires_scope_review() -> None:
    data = evidence()
    data["actors"]["customer_a"]["object_grants"] = [grant("Account", read=True)]
    assert "customer_a:Account:field_and_record_scope_required" in review(data)["review_gaps"]


def test_guest_identity_read_is_disallowed() -> None:
    data = evidence()
    data["actors"]["guest"]["object_grants"] = [grant("Contact", read=True)]
    assert review(data)["observed_disallowed_grants"] == [
        {"actor": "guest", "object": "Contact", "grant": "read"}
    ]


def test_incomplete_inventory_requires_review() -> None:
    data = evidence()
    data["actors"]["guest"]["sources_complete"] = False
    assert "guest:source_inventory_incomplete" in review(data)["review_gaps"]


def test_invalid_flag_is_rejected() -> None:
    data = evidence()
    row = grant("Case")
    row["read"] = "false"
    data["actors"]["customer_a"]["object_grants"] = [row]
    with pytest.raises(ValueError, match="boolean"):
        review(data)
