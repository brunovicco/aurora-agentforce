import base64
import json
from datetime import UTC, datetime, timedelta

import pytest

from aurora_orders.application.customer_sessions import (
    InvalidCustomerSession,
    mint_demo_session,
    validate_signing_key,
    verify_customer_session,
)
from tests.conftest import NOW, TEST_SESSION_KEY


def issue(*, customer: str = "customer-demo-001", session: str = "s-01") -> str:
    return mint_demo_session(
        signing_key=TEST_SESSION_KEY,
        customer_ref=customer,
        session_id=session,
        now=NOW,
    )


def test_round_trip_and_customer_scoping() -> None:
    verified = verify_customer_session(issue(), signing_key=TEST_SESSION_KEY, now=NOW)
    assert verified.customer_ref == "customer-demo-001"
    assert verified.session_id == "s-01"


@pytest.mark.parametrize("token", ["", "garbage", "a.b.c", "?.abc", "a.!", "a" * 5000])
def test_malformed_tokens_rejected(token: str) -> None:
    with pytest.raises(InvalidCustomerSession):
        verify_customer_session(token, signing_key=TEST_SESSION_KEY, now=NOW)


def test_tampering_with_payload_rejected() -> None:
    payload, signature = issue().split(".")
    altered = payload[:-1] + ("A" if payload[-1] != "A" else "B")
    with pytest.raises(InvalidCustomerSession):
        verify_customer_session(f"{altered}.{signature}", signing_key=TEST_SESSION_KEY, now=NOW)


def test_invalid_signature_key_rejected() -> None:
    with pytest.raises(InvalidCustomerSession):
        verify_customer_session(
            issue(), signing_key="another-equally-long-signing-secret-0000000", now=NOW
        )


def test_expired_and_future_issued_sessions_rejected() -> None:
    with pytest.raises(InvalidCustomerSession):
        verify_customer_session(issue(), signing_key=TEST_SESSION_KEY, now=NOW + timedelta(minutes=5))
    with pytest.raises(InvalidCustomerSession):
        verify_customer_session(issue(), signing_key=TEST_SESSION_KEY, now=NOW - timedelta(seconds=1))


def test_revoked_session_is_rejected() -> None:
    with pytest.raises(InvalidCustomerSession):
        verify_customer_session(
            issue(),
            signing_key=TEST_SESSION_KEY,
            now=NOW,
            revoked_session_ids=frozenset({"s-01"}),
        )


@pytest.mark.parametrize("ttl", [0, 901])
def test_minter_rejects_unsafe_ttl(ttl: int) -> None:
    with pytest.raises(ValueError, match="TTL"):
        mint_demo_session(
            signing_key=TEST_SESSION_KEY,
            customer_ref="customer-demo-001",
            session_id="s-01",
            now=NOW,
            ttl_seconds=ttl,
        )


def test_minter_rejects_invalid_identifiers_and_naive_time() -> None:
    with pytest.raises(ValueError, match="opaque"):
        mint_demo_session(
            signing_key=TEST_SESSION_KEY,
            customer_ref="email@example.com",
            session_id="s-01",
            now=NOW,
        )
    with pytest.raises(ValueError, match="timezone-aware"):
        mint_demo_session(
            signing_key=TEST_SESSION_KEY,
            customer_ref="customer-demo-001",
            session_id="s-01",
            now=datetime(2026, 11, 5),
        )


def test_minter_rejects_weak_secret() -> None:
    with pytest.raises(ValueError, match="AURORA_CUSTOMER_SESSION_SECRET"):
        validate_signing_key("short")


def test_utc_conversion_is_stable() -> None:
    offset_time = NOW.astimezone(UTC)
    token = mint_demo_session(
        signing_key=TEST_SESSION_KEY,
        customer_ref="customer-demo-001",
        session_id="s-02",
        now=offset_time,
    )
    assert verify_customer_session(token, signing_key=TEST_SESSION_KEY, now=NOW).session_id == "s-02"


def test_signature_cannot_be_reused_with_a_different_subject() -> None:
    payload, signature = issue().split(".")
    claims = json.loads(base64.urlsafe_b64decode(payload + "=="))
    claims["sub"] = "customer-demo-002"
    changed = base64.urlsafe_b64encode(json.dumps(claims).encode()).decode().rstrip("=")
    with pytest.raises(InvalidCustomerSession):
        verify_customer_session(f"{changed}.{signature}", signing_key=TEST_SESSION_KEY, now=NOW)
