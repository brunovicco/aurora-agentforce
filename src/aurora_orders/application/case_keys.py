"""Stable request keys compatible with Salesforce case-insensitive Text(100)."""

import hashlib

from aurora_orders.domain.policy import Order

LEGACY_CUSTOMERS = frozenset({"customer-demo-001", "customer-demo-002"})


def case_request_key(order: Order) -> str:
    """Preserve known demo keys; hash other exact identities without case folding."""
    if order.customer_ref in LEGACY_CUSTOMERS:
        return f"{order.customer_ref}:{order.order_id}:post-sale"
    payload = f"{order.customer_ref}:{order.order_id}:post-sale"
    return f"v1:{hashlib.sha256(payload.encode()).hexdigest()}"
