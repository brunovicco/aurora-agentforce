"""Read operations restricted to the customer configured by the server."""

from collections.abc import Sequence

from aurora_orders.domain.policy import Order


class OrderUnavailable(Exception):
    """Hide whether an order is missing or belongs to another customer."""


def find_order(orders: Sequence[Order], *, order_id: str, customer_ref: str) -> Order:
    """Authorize before returning an order; never trust a customer ID from the agent."""
    for order in orders:
        if order.order_id == order_id and order.customer_ref == customer_ref:
            return order
    raise OrderUnavailable
