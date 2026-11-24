from datetime import timedelta

import pytest
from fastapi.testclient import TestClient

from aurora_orders.application.context_broker import ContextBroker
from aurora_orders.entrypoints.api import create_app
from tests.conftest import NOW, TEST_API_KEY, TEST_SESSION_KEY, TODAY
from tests.test_verified_api import session_headers

BROKER_KEY = "synthetic-broker-credential-only-for-tests"
ROUTE = "/v1/context/resolve"
PAYLOAD = {"conversation_id": "conversation-1", "execution_user_id": "user-1"}


def register(broker: ContextBroker, customer: str = "customer-demo-001") -> None:
    broker.register(
        conversation_id="conversation-1",
        execution_user_id="user-1",
        customer_ref=customer,
        expires_at=NOW + timedelta(minutes=2),
        now=NOW,
    )


def make_client(broker: ContextBroker) -> TestClient:
    return TestClient(
        create_app(
            api_key=TEST_API_KEY,
            session_signing_key=TEST_SESSION_KEY,
            session_clock=lambda: NOW,
            clock=lambda: TODAY,
            context_broker=broker,
            broker_api_key=BROKER_KEY,
            allow_unverified_demo_reads=False,
        )
    )


def resolve(client: TestClient) -> dict[str, str]:
    result = client.post(ROUTE, json=PAYLOAD, headers={"X-Aurora-Broker-Key": BROKER_KEY})
    assert result.status_code == 200
    assert result.headers["Cache-Control"] == "no-store"
    return {"X-API-Key": TEST_API_KEY, "X-Aurora-Customer-Session": result.json()["session_token"]}


def test_broker_issue_scope_replace_and_revoke() -> None:
    broker = ContextBroker()
    register(broker)
    with make_client(broker) as client:
        headers = resolve(client)
        assert client.get("/verified/orders/AUR-1001", headers=headers).status_code == 200
        assert client.get("/verified/orders/AUR-9001", headers=headers).status_code == 404
        register(broker, "customer-demo-002")
        assert client.get("/verified/orders/AUR-1001", headers=headers).status_code == 401
        second = resolve(client)
        assert client.get("/verified/orders/AUR-9001", headers=second).status_code == 200
        broker.revoke("conversation-1")
        assert client.get("/verified/orders/AUR-9001", headers=second).status_code == 401
        assert client.post(
            ROUTE, json=PAYLOAD, headers={"X-Aurora-Broker-Key": BROKER_KEY}
        ).status_code == 404


def test_broker_credentials_and_scope() -> None:
    broker = ContextBroker()
    register(broker)
    with make_client(broker) as client:
        for key in ("", TEST_API_KEY, TEST_SESSION_KEY):
            assert client.post(
                ROUTE, json=PAYLOAD, headers={"X-Aurora-Broker-Key": key}
            ).status_code == 401
        for payload in (
            {**PAYLOAD, "execution_user_id": "user-2"},
            {**PAYLOAD, "conversation_id": "conversation-2"},
        ):
            assert client.post(
                ROUTE, json=payload, headers={"X-Aurora-Broker-Key": BROKER_KEY}
            ).status_code == 404
        assert client.get(
            "/verified/orders/AUR-1001", headers=session_headers()
        ).status_code == 401
        assert ROUTE not in client.get("/openapi.json").json()["paths"]


def test_broker_expiry_and_invalid_registration() -> None:
    broker = ContextBroker()
    register(broker)
    assert broker.resolve("conversation-1", "user-1", NOW + timedelta(minutes=2)) is None
    with pytest.raises(ValueError, match="Invalid trusted binding"):
        broker.register(
            conversation_id="conversation-1",
            execution_user_id="user-1",
            customer_ref="invalid customer",
            expires_at=NOW,
            now=NOW
        )


def test_broker_is_opt_in_and_requires_separate_credentials() -> None:
    with TestClient(create_app(api_key=TEST_API_KEY)) as client:
        assert client.post(ROUTE, json=PAYLOAD).status_code == 404
    with pytest.raises(ValueError, match="together"):
        create_app(api_key=TEST_API_KEY, context_broker=ContextBroker())
    with pytest.raises(ValueError, match="separate credential"):
        create_app(
            api_key=TEST_API_KEY,
            session_signing_key=TEST_SESSION_KEY,
            context_broker=ContextBroker(),
            broker_api_key=TEST_API_KEY,
            allow_unverified_demo_reads=False,
        )
