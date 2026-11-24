import logging

import pytest
from fastapi.testclient import TestClient

from aurora_orders.application.broker_security import BrokerRateLimit
from aurora_orders.application.context_broker import BindingStoreUnavailable, ContextBroker
from aurora_orders.entrypoints.api import create_app
from tests.conftest import NOW, TEST_API_KEY, TEST_SESSION_KEY
from tests.test_context_broker import BROKER_KEY, PAYLOAD, ROUTE, register, resolve


def test_scope_policy_rate_limit_and_safe_audit(caplog: pytest.LogCaptureFixture) -> None:
    broker = ContextBroker()
    register(broker)
    app = create_app(
        api_key=TEST_API_KEY,
        session_signing_key=TEST_SESSION_KEY,
        session_clock=lambda: NOW,
        context_broker=broker,
        broker_api_key=BROKER_KEY,
        broker_scope=lambda conversation, user: conversation == "conversation-1"
        and user == "user-1",
        broker_rate_limit=BrokerRateLimit(3),
        allow_unverified_demo_reads=False,
    )
    with TestClient(app) as client, caplog.at_level(logging.INFO, logger="aurora.broker"):
        assert client.post(ROUTE, json=PAYLOAD).status_code == 401
        denied = client.post(
            ROUTE,
            json={**PAYLOAD, "conversation_id": "conversation-2"},
            headers={"X-Aurora-Broker-Key": BROKER_KEY},
        )
        assert denied.status_code == 404
        headers = resolve(client)
        limited = client.post(ROUTE, json=PAYLOAD, headers={"X-Aurora-Broker-Key": BROKER_KEY})
        assert limited.status_code == 429
        assert limited.headers["Cache-Control"] == "no-store"
    assert "broker_credential_denied" in caplog.text
    assert "broker_scope_denied" in caplog.text
    assert "broker_session_issued" in caplog.text
    assert "broker_rate_limited" in caplog.text
    assert headers["X-Aurora-Customer-Session"] not in caplog.text
    assert BROKER_KEY not in caplog.text


def test_rate_limit_resets() -> None:
    time = [0.0]
    limiter = BrokerRateLimit(1, clock=lambda: time[0])
    assert limiter.admit()
    assert not limiter.admit()
    time[0] = 60.0
    assert limiter.admit()
    with pytest.raises(ValueError, match="positive"):
        BrokerRateLimit(0)


def test_store_failure_denies_without_diagnostic(monkeypatch: pytest.MonkeyPatch) -> None:
    broker = ContextBroker()
    register(broker)
    app = create_app(
        api_key=TEST_API_KEY,
        session_signing_key=TEST_SESSION_KEY,
        session_clock=lambda: NOW,
        context_broker=broker,
        broker_api_key=BROKER_KEY,
        broker_scope=lambda conversation, user: True,
        allow_unverified_demo_reads=False,
    )

    def unavailable(*args: object) -> None:
        raise BindingStoreUnavailable("internal diagnostic")

    with TestClient(app) as client:
        headers = resolve(client)
        monkeypatch.setattr(broker, "resolve", unavailable)
        monkeypatch.setattr(broker, "is_active", unavailable)
        result = client.post(ROUTE, json=PAYLOAD, headers={"X-Aurora-Broker-Key": BROKER_KEY})
        assert result.status_code == 503
        assert "internal diagnostic" not in result.text
        result = client.get("/verified/orders/AUR-1001", headers=headers)
        assert result.status_code == 503
        assert "internal diagnostic" not in result.text


def test_scope_required() -> None:
    with pytest.raises(ValueError, match="scope policy"):
        create_app(
            api_key=TEST_API_KEY,
            session_signing_key=TEST_SESSION_KEY,
            context_broker=ContextBroker(),
            broker_api_key=BROKER_KEY,
            allow_unverified_demo_reads=False,
        )
