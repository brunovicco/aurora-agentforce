from datetime import timedelta

import pytest
from fastapi.testclient import TestClient

from aurora_orders.application.customer_sessions import mint_demo_session
from aurora_orders.entrypoints.api import create_app
from tests.conftest import NOW, TEST_API_KEY, TEST_SESSION_KEY, TODAY

VERIFIED_ROUTES = [
    "/verified/orders/{}",
    "/verified/orders/{}/return-eligibility",
]
LEGACY_ROUTES = ["/orders/{}", "/orders/{}/return-eligibility"]


def session_headers(
    *, customer: str = "customer-demo-001", session: str = "s-01"
) -> dict[str, str]:
    token = mint_demo_session(
        signing_key=TEST_SESSION_KEY,
        customer_ref=customer,
        session_id=session,
        now=NOW,
    )
    return {"X-API-Key": TEST_API_KEY, "X-Aurora-Customer-Session": token}


@pytest.fixture
def secure_client() -> TestClient:
    return TestClient(
        create_app(
            api_key=TEST_API_KEY,
            clock=lambda: TODAY,
            session_clock=lambda: NOW,
            session_signing_key=TEST_SESSION_KEY,
        )
    )


@pytest.mark.parametrize("route", VERIFIED_ROUTES)
def test_verified_reads_are_customer_scoped(secure_client: TestClient, route: str) -> None:
    one = secure_client.get(route.format("AUR-1001"), headers=session_headers())
    cross = secure_client.get(route.format("AUR-9001"), headers=session_headers())
    missing = secure_client.get(route.format("AUR-9999"), headers=session_headers())
    other = secure_client.get(
        route.format("AUR-9001"), headers=session_headers(customer="customer-demo-002")
    )
    assert one.status_code == other.status_code == 200
    assert cross.status_code == missing.status_code == 404
    assert cross.json() == missing.json() == {"detail": "Order unavailable."}


@pytest.mark.parametrize("route", VERIFIED_ROUTES)
def test_session_cannot_be_overridden_by_chat_parameters(
    secure_client: TestClient, route: str
) -> None:
    response = secure_client.get(
        route.format("AUR-9001"),
        params={"customer_ref": "customer-demo-002", "verified": "true"},
        headers=session_headers(),
    )
    assert response.status_code == 404


@pytest.mark.parametrize("route", VERIFIED_ROUTES)
def test_missing_or_invalid_session_rejected(secure_client: TestClient, route: str) -> None:
    url = route.format("AUR-1001")
    for value in (None, "untrusted", session_headers()["X-Aurora-Customer-Session"] + "x"):
        headers = {"X-API-Key": TEST_API_KEY}
        if value is not None:
            headers["X-Aurora-Customer-Session"] = value
        response = secure_client.get(url, headers=headers)
        assert response.status_code == 401
        assert response.json() == {"detail": "Invalid customer session."}


@pytest.mark.parametrize("route", VERIFIED_ROUTES)
def test_integration_auth_remains_independent(secure_client: TestClient, route: str) -> None:
    url = route.format("AUR-1001")
    session = session_headers()
    del session["X-API-Key"]
    assert secure_client.get(url, headers=session).status_code == 401


@pytest.mark.parametrize("route", LEGACY_ROUTES)
def test_unverified_legacy_reads_are_disabled_by_default(
    secure_client: TestClient, route: str
) -> None:
    response = secure_client.get(route.format("AUR-1001"), headers={"X-API-Key": TEST_API_KEY})
    assert response.status_code == 403
    assert response.json() == {"detail": "Unverified demo reads are disabled."}


def test_expired_session_rejected_in_api() -> None:
    app = create_app(
        api_key=TEST_API_KEY,
        clock=lambda: TODAY,
        session_clock=lambda: NOW + timedelta(minutes=6),
        session_signing_key=TEST_SESSION_KEY,
    )
    with TestClient(app) as client:
        assert client.get("/verified/orders/AUR-1001", headers=session_headers()).status_code == 401


def test_revoked_session_rejected_in_api() -> None:
    app = create_app(
        api_key=TEST_API_KEY,
        clock=lambda: TODAY,
        session_clock=lambda: NOW,
        session_signing_key=TEST_SESSION_KEY,
        revoked_session_ids=frozenset({"s-01"}),
    )
    with TestClient(app) as client:
        assert client.get("/verified/orders/AUR-1001", headers=session_headers()).status_code == 401


def test_verified_routes_fail_closed_without_session_signing_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("AURORA_CUSTOMER_SESSION_SECRET", raising=False)
    app = create_app(api_key=TEST_API_KEY, clock=lambda: TODAY)
    with TestClient(app) as client:
        response = client.get("/verified/orders/AUR-1001", headers=session_headers())
        assert response.status_code == 503
        assert response.json() == {"detail": "Verified customer reads unavailable."}


def test_no_public_token_minting_endpoint(secure_client: TestClient) -> None:
    paths = set(secure_client.get("/openapi.json").json()["paths"])
    assert all("session" not in path and "token" not in path for path in paths)
    assert "/verified/orders/{order_id}" in paths
