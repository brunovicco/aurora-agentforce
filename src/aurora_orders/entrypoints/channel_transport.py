"""Reference transport for trusted runtime actions; not a public action endpoint."""

import re
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal

from aurora_orders.application.trusted_channel import BindingResolver, resolve_channel_binding

type Operation = Literal["order", "return-eligibility", "case-authorization"]
type Transport = Callable[[str, dict[str, str]], tuple[int, dict[str, object]]]

ORDER_ID = re.compile(r"^AUR-[0-9]{4}$")


@dataclass(frozen=True, slots=True)
class TrustedActionTransport:
    """Bind an action facade to trusted runtime context, never chat arguments."""

    conversation_id: str
    resolver: BindingResolver = field(repr=False)
    signing_key: str = field(repr=False)
    integration_key: str = field(repr=False)
    clock: Callable[[], datetime] = field(repr=False)
    transport: Transport = field(repr=False)
    revoked_sessions: Callable[[], frozenset[str]] = field(repr=False)

    def execute(self, operation: Operation, order_id: str) -> tuple[int, dict[str, object]]:
        """Validate context on each call and inject credentials only in the transport."""
        if not ORDER_ID.fullmatch(order_id):
            raise ValueError("Invalid order ID.")
        if operation not in ("order", "return-eligibility", "case-authorization"):
            raise ValueError("Unsupported operation.")
        binding = resolve_channel_binding(
            self.conversation_id,
            resolver=self.resolver,
            signing_key=self.signing_key,
            now=self.clock(),
            revoked_session_ids=self.revoked_sessions(),
        )
        path = f"/verified/orders/{order_id}"
        if operation != "order":
            path += f"/{operation}"
        return self.transport(
            path,
            {
                "X-API-Key": self.integration_key,
                "X-Aurora-Customer-Session": binding.session_token,
            },
        )
