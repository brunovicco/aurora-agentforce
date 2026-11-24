"""Resolve pre-authenticated conversation bindings outside agent-controlled input."""

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime

from aurora_orders.application.customer_sessions import (
    InvalidCustomerSession,
    VerifiedCustomer,
    verify_customer_session,
)


@dataclass(frozen=True, slots=True)
class ChannelBinding:
    """A binding established by trusted channel infrastructure after authentication."""

    conversation_id: str
    customer: VerifiedCustomer
    session_token: str = field(repr=False)


type BindingResolver = Callable[[str], ChannelBinding | None]


def resolve_channel_customer(
    conversation_id: str,
    *,
    resolver: BindingResolver,
    signing_key: str,
    now: datetime,
    revoked_session_ids: frozenset[str] = frozenset(),
) -> VerifiedCustomer:
    """Fail closed unless the current binding matches verified signed claims."""
    if not conversation_id or len(conversation_id) > 128:
        raise InvalidCustomerSession
    binding = resolver(conversation_id)
    if binding is None or binding.conversation_id != conversation_id:
        raise InvalidCustomerSession
    customer = verify_customer_session(
        binding.session_token,
        signing_key=signing_key,
        now=now,
        revoked_session_ids=revoked_session_ids,
    )
    if customer != binding.customer:
        raise InvalidCustomerSession
    return customer
