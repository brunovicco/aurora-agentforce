import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from jsonschema import Draft4Validator
from openapi_spec_validator import validate

from aurora_orders.entrypoints.api import create_app
from tests.conftest import NOW, TEST_API_KEY, TEST_SESSION_KEY, TODAY
from tests.test_verified_api import session_headers

CONTRACT = json.loads(
    (Path(__file__).parents[1] / "salesforce" / "openapi.verified.json").read_text()
)
CASE_ROUTE = "/verified/orders/{order_id}/case-authorization"


@pytest.fixture
def gateway() -> TestClient:
    return TestClient(
        create_app(
            api_key=TEST_API_KEY,
            clock=lambda: TODAY,
            session_clock=lambda: NOW,
            session_signing_key=TEST_SESSION_KEY,
            allow_unverified_demo_reads=False,
        )
    )


def test_verified_contract_is_valid_and_matches_routes(gateway: TestClient) -> None:
    validate(CONTRACT)
    live = gateway.get("/openapi.json").json()
    for path, operation in CONTRACT["paths"].items():
        assert operation["get"]["operationId"] == live["paths"][path]["get"]["operationId"]
    assert CONTRACT["security"] == [{"ApiKey": [], "CustomerSession": []}]


@pytest.mark.parametrize("path", list(CONTRACT["paths"]))
@pytest.mark.parametrize(
    ("order", "customer", "status"),
    [
        ("AUR-1001", "customer-demo-001", 200),
        ("AUR-9001", "customer-demo-002", 200),
        ("AUR-9001", "customer-demo-001", 404),
        ("AUR-9999", "customer-demo-001", 404),
        ("invalid", "customer-demo-001", 422),
    ],
)
def test_verified_contract_responses(
    gateway: TestClient, path: str, order: str, customer: str, status: int
) -> None:
    response = gateway.get(
        path.replace("{order_id}", order), headers=session_headers(customer=customer)
    )
    assert response.status_code == status
    schema = CONTRACT["paths"][path]["get"]["responses"][str(status)]["content"][
        "application/json"
    ]["schema"]
    Draft4Validator(schema).validate(response.json())


def test_case_key_is_stable_across_sessions_and_not_agent_controlled(gateway: TestClient) -> None:
    path = CASE_ROUTE.replace("{order_id}", "AUR-1001")
    first = gateway.get(path, headers=session_headers())
    second = gateway.get(
        path,
        headers=session_headers(session="another-session"),
        params={"customer_ref": "customer-demo-002", "request_key": "forged"},
    )
    assert first.json() == second.json()
    assert first.json() == {
        "order_id": "AUR-1001",
        "request_key": "customer-demo-001:AUR-1001:post-sale",
    }


def test_case_key_for_second_customer(gateway: TestClient) -> None:
    response = gateway.get(
        CASE_ROUTE.replace("{order_id}", "AUR-9001"),
        headers=session_headers(customer="customer-demo-002"),
    )
    assert response.json()["request_key"] == "customer-demo-002:AUR-9001:post-sale"


def test_case_authorization_requires_both_credentials(gateway: TestClient) -> None:
    path = CASE_ROUTE.replace("{order_id}", "AUR-1001")
    assert gateway.get(path, headers={"X-API-Key": TEST_API_KEY}).status_code == 401
    headers = session_headers()
    del headers["X-API-Key"]
    assert gateway.get(path, headers=headers).status_code == 401


def test_case_authorization_does_not_disclose_cross_customer_key(gateway: TestClient) -> None:
    denied = gateway.get(CASE_ROUTE.replace("{order_id}", "AUR-9001"), headers=session_headers())
    missing = gateway.get(CASE_ROUTE.replace("{order_id}", "AUR-9999"), headers=session_headers())
    assert denied.status_code == missing.status_code == 404
    assert denied.json() == missing.json() == {"detail": "Order unavailable."}
