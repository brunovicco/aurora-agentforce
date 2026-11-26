"""Tests for synthetic account record-access evidence."""

from typing import Any

from scripts.portal_record_access import inspect_access


def users() -> list[dict[str, Any]]:
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


def test_cross_account_read_is_flagged() -> None:
    report = inspect_access(
        users(),
        {
            "customer_a": [
                {"RecordId": "account-A", "HasReadAccess": True, "HasEditAccess": False},
                {"RecordId": "account-B", "HasReadAccess": True, "HasEditAccess": False},
            ]
        },
    )
    assert report["account_access"][1]["outcome"] == "review_required"
    assert report["complete"] is False
    assert report["runtime_access_verified"] is False


def test_missing_row_is_unknown() -> None:
    report = inspect_access(users(), {"customer_a": []})
    assert all(row["outcome"] == "unknown" for row in report["account_access"])
