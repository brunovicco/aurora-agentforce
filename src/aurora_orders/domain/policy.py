"""A fictional, versioned return policy with deterministic decisions."""

from dataclasses import dataclass
from datetime import date
from typing import Literal

POLICY_REFERENCE = "AURORA-DEMO-RETURNS-v1"
RETURN_WINDOW_DAYS = 30
type OrderStatus = Literal["processing", "shipped", "delivered", "cancelled"]


@dataclass(frozen=True)
class Order:
    """Minimal synthetic order; no personal or payment data."""

    order_id: str
    customer_ref: str
    product: str
    status: OrderStatus
    delivered_on: date | None = None
    returnable: bool = True


@dataclass(frozen=True)
class ReturnDecision:
    """Explain a policy result without delegating the rule to a language model."""

    eligible: bool
    reason_code: str
    reason: str
    policy_reference: str = POLICY_REFERENCE


def evaluate_return(order: Order, *, today: date) -> ReturnDecision:
    """Accept delivered, returnable items through day 30, inclusive, in UTC."""
    if order.status != "delivered":
        return ReturnDecision(False, "NOT_DELIVERED", "O pedido ainda não foi entregue.")
    if order.delivered_on is None or order.delivered_on > today:
        return ReturnDecision(False, "INVALID_DELIVERY_DATE", "A data de entrega exige revisão.")
    if not order.returnable:
        return ReturnDecision(False, "EXCLUDED_ITEM", "Item excluído da política fictícia da demo.")
    if (today - order.delivered_on).days > RETURN_WINDOW_DAYS:
        return ReturnDecision(False, "WINDOW_EXPIRED", "O prazo fictício de 30 dias foi excedido.")
    return ReturnDecision(True, "ELIGIBLE", "Item elegível pela política fictícia de 30 dias.")
