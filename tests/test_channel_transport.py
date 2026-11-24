from datetime import timedelta

import pytest
from fastapi.testclient import TestClient

from aurora_orders.application.customer_sessions import InvalidCustomerSession
from aurora_orders.entrypoints.api import create_app
from aurora_orders.entrypoints.channel_transport import Operation, TrustedActionTransport
from tests.conftest import NOW, TEST_API_KEY, TEST_SESSION_KEY, TODAY
from tests.test_trusted_channel import binding


@pytest.mark.parametrize("operation", ["order", "return-eligibility", "case-authorization"])
def test_transport_enforces_customer_scope(operation: Operation) -> None:
    app = create_app(
        api_key=TEST_API_KEY,
        session_signing_key=TEST_SESSION_KEY,
        clock=lambda: TODAY,
        session_clock=lambda: NOW,
    )
    first = binding()
    second = binding("conversation-2", "customer-demo-002", "session-2")
    bindings = {item.conversation_id: item for item in (first, second)}
    with TestClient(app) as client:

        def send(path: str, headers: dict[str, str]) -> tuple[int, dict[str, object]]:
            response = client.get(path, headers=headers)
            return response.status_code, dict(response.json())

        def facade(conversation: str) -> TrustedActionTransport:
            return TrustedActionTransport(
                conversation,
                bindings.get,
                TEST_SESSION_KEY,
                TEST_API_KEY,
                lambda: NOW,
                send,
                frozenset,
            )

        one = facade(first.conversation_id)
        two = facade(second.conversation_id)
        assert one.execute(operation, "AUR-1001")[0] == 200
        assert two.execute(operation, "AUR-9001")[0] == 200
        assert one.execute(operation, "AUR-9001") == two.execute(operation, "AUR-9999")
        assert one.execute(operation, "AUR-9001")[0] == 404
        assert TEST_API_KEY not in repr(one)
        assert TEST_SESSION_KEY not in repr(one)


@pytest.mark.parametrize("mode", ["missing", "expired", "revoked", "invalid-order", "invalid-op"])
def test_denial_does_not_dispatch(mode: str) -> None:
    first = binding()

    def send(path: str, headers: dict[str, str]) -> tuple[int, dict[str, object]]:
        pytest.fail("Denied action must not reach transport.")

    action = TrustedActionTransport(
        first.conversation_id,
        lambda _: None if mode == "missing" else first,
        TEST_SESSION_KEY,
        TEST_API_KEY,
        lambda: NOW + timedelta(minutes=6) if mode == "expired" else NOW,
        send,
        lambda: frozenset({"session-1"}) if mode == "revoked" else frozenset(),
    )
    with pytest.raises((InvalidCustomerSession, ValueError)):
        action.execute(
            "invalid" if mode == "invalid-op" else "order",  # type: ignore[arg-type]
            "../health" if mode == "invalid-order" else "AUR-1001",
        )


def test_revocation_is_checked_again_on_each_call() -> None:
    first = binding()
    revoked: set[str] = set()
    action = TrustedActionTransport(
        first.conversation_id,
        lambda _: first,
        TEST_SESSION_KEY,
        TEST_API_KEY,
        lambda: NOW,
        lambda path, headers: (200, {}),
        lambda: frozenset(revoked),
    )
    assert action.execute("order", "AUR-1001")[0] == 200
    revoked.add("session-1")
    with pytest.raises(InvalidCustomerSession):
        action.execute("order", "AUR-1001")
