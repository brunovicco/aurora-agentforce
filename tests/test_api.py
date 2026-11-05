from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from aurora_orders.entrypoints.api import create_app, utc_today
from tests.conftest import TEST_API_KEY

ROUTES = ["/orders/{}", "/orders/{}/return-eligibility"]


@pytest.mark.parametrize("route", ROUTES)
@pytest.mark.parametrize("supplied_headers", [{}, {"X-API-Key": "wrong"}])
def test_reads_require_valid_authentication(
    client: TestClient, route: str, supplied_headers: dict[str, str]
) -> None:
    response = client.get(route.format("AUR-1001"), headers=supplied_headers)
    assert response.status_code == 401
    assert response.json() == {"detail": "Credencial inválida."}


@pytest.mark.parametrize("route", ROUTES)
def test_other_customer_and_missing_orders_have_same_response(
    client: TestClient, headers: dict[str, str], route: str
) -> None:
    denied = client.get(route.format("AUR-9001"), headers=headers)
    missing = client.get(route.format("AUR-9999"), headers=headers)
    assert denied.status_code == missing.status_code == 404
    assert denied.json() == missing.json() == {"detail": "Pedido indisponível."}


@pytest.mark.parametrize("route", ROUTES)
def test_agent_cannot_override_customer_context(
    client: TestClient, headers: dict[str, str], route: str
) -> None:
    response = client.get(
        route.format("AUR-9001"), params={"customer_ref": "customer-demo-002"}, headers=headers
    )
    assert response.status_code == 404


@pytest.mark.parametrize("route", ROUTES)
def test_invalid_order_format_is_rejected(
    client: TestClient, headers: dict[str, str], route: str
) -> None:
    assert client.get(route.format("invalid"), headers=headers).status_code == 422


def test_order_response_exposes_only_needed_fields(
    client: TestClient, headers: dict[str, str]
) -> None:
    response = client.get("/orders/AUR-1003", headers=headers)
    assert response.status_code == 200
    assert response.json() == {
        "order_id": "AUR-1003",
        "product": "Mouse Aurora",
        "status": "shipped",
    }


@pytest.mark.parametrize(
    ("order_id", "eligible", "code"),
    [
        ("AUR-1001", True, "ELIGIBLE"),
        ("AUR-1002", False, "WINDOW_EXPIRED"),
        ("AUR-1003", False, "NOT_DELIVERED"),
        ("AUR-1004", True, "ELIGIBLE"),
        ("AUR-1005", False, "EXCLUDED_ITEM"),
        ("AUR-1006", False, "NOT_DELIVERED"),
    ],
)
def test_eligibility_action_returns_explainable_results(
    client: TestClient, headers: dict[str, str], order_id: str, eligible: bool, code: str
) -> None:
    response = client.get(f"/orders/{order_id}/return-eligibility", headers=headers)
    assert response.status_code == 200
    result = response.json()
    assert result["eligible"] is eligible
    assert result["reason_code"] == code
    assert result["policy_reference"] == "AURORA-DEMO-RETURNS-v1"
    assert result["evaluated_on"] == "2026-11-05"


@pytest.mark.parametrize("value", [None, "short", " " * 40])
def test_startup_fails_without_a_usable_credential(
    monkeypatch: pytest.MonkeyPatch, value: str | None
) -> None:
    monkeypatch.delenv("AURORA_API_KEY", raising=False)
    with pytest.raises(ValueError, match="AURORA_API_KEY"):
        create_app(api_key=value)


def test_reads_credential_from_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AURORA_API_KEY", TEST_API_KEY)
    assert create_app().title == "Aurora Orders Demo"


def test_health_contains_no_business_data(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_production_clock_uses_utc() -> None:
    before = datetime.now(UTC).date()
    observed = utc_today()
    after = datetime.now(UTC).date()
    assert before <= observed <= after
