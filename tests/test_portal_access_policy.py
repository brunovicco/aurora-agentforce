"""Protect the initial portal's restrictive access policy contract."""

import json

from scripts import portal_prepare as portal


def test_initial_portal_policy_is_restrictive() -> None:
    policy = json.loads((portal.ROOT.parent / "portal-access-policy.json").read_text())
    assert policy["status"] == "target_not_verified"
    assert policy["profile"] == "Aurora Customer"
    assert set(policy["principals"]) == {"guest", "customer_a", "customer_b"}
    objects = policy["objects"]
    assert set(objects) == {
        "Account",
        "Contact",
        "User",
        "Case",
        "AuroraCaseApproval__c",
        "Order",
        "MessagingSession",
        "MessagingEndUser",
    }
    for name, grants in objects.items():
        expected = "own_only_if_required" if name in {"Account", "Contact", "User"} else "deny"
        assert grants["read"] == expected
        for action in ("create", "update", "delete", "view_all", "modify_all"):
            assert grants[action] is False
    assert set(policy["business_operations"].values()) == {"deny"}
