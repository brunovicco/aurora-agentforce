from datetime import timedelta

import pytest

from aurora_orders.application.customer_sessions import (
    InvalidCustomerSession,
    VerifiedCustomer,
    mint_demo_session,
)
from aurora_orders.application.trusted_channel import ChannelBinding, resolve_channel_customer
from tests.conftest import NOW, TEST_SESSION_KEY


def binding(
    conversation: str = "conversation-1",
    customer: str = "customer-demo-001",
    session: str = "session-1",
) -> ChannelBinding:
    token = mint_demo_session(
        signing_key=TEST_SESSION_KEY,
        customer_ref=customer,
        session_id=session,
        now=NOW,
    )
    return ChannelBinding(conversation, VerifiedCustomer(customer, session), token)


def test_resolves_only_current_conversation() -> None:
    first = binding()
    second = binding("conversation-2", "customer-demo-002", "session-2")
    bindings = {item.conversation_id: item for item in (first, second)}
    for item in (first, second):
        assert (
            resolve_channel_customer(
                item.conversation_id,
                resolver=bindings.get,
                signing_key=TEST_SESSION_KEY,
                now=NOW,
            )
            == item.customer
        )
    assert first.session_token not in repr(first)


@pytest.mark.parametrize("conversation", ["", "x" * 129, "unknown", "conversation-2"])
def test_missing_or_wrong_conversation_is_denied(conversation: str) -> None:
    first = binding()
    with pytest.raises(InvalidCustomerSession):
        resolve_channel_customer(
            conversation,
            resolver=lambda _: None if conversation == "unknown" else first,
            signing_key=TEST_SESSION_KEY,
            now=NOW,
        )


@pytest.mark.parametrize("mode", ["expired", "revoked", "tampered", "wrong-customer", "wrong-session"])
def test_invalid_binding_is_denied(mode: str) -> None:
    first = binding()
    customer = first.customer
    token = first.session_token
    if mode == "wrong-customer":
        customer = VerifiedCustomer("customer-demo-002", customer.session_id)
    if mode == "wrong-session":
        customer = VerifiedCustomer(customer.customer_ref, "session-2")
    if mode == "tampered":
        token += "x"
    current = ChannelBinding(first.conversation_id, customer, token)
    with pytest.raises(InvalidCustomerSession):
        resolve_channel_customer(
            first.conversation_id,
            resolver=lambda _: current,
            signing_key=TEST_SESSION_KEY,
            now=NOW + timedelta(minutes=6) if mode == "expired" else NOW,
            revoked_session_ids=frozenset({"session-1"}) if mode == "revoked" else frozenset(),
        )
