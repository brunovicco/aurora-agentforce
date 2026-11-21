"""Authenticated HTTP reads; Agentforce and Salesforce own the conversation and cases."""

import os
import secrets
from collections.abc import Callable
from datetime import UTC, date, datetime
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Path, Security
from fastapi.security import APIKeyHeader
from pydantic import BaseModel, ConfigDict

from aurora_orders.adapters.demo_orders import DEMO_CUSTOMER_REF, demo_orders
from aurora_orders.application.orders import OrderUnavailable, find_order
from aurora_orders.domain.policy import Order, OrderStatus, evaluate_return

type OrderId = Annotated[str, Path(pattern=r"^AUR-[0-9]{4}$")]


class OrderResponse(BaseModel):
    """Public order fields suitable for an agent action."""

    model_config = ConfigDict(extra="forbid")
    order_id: str
    product: str
    status: OrderStatus


class EligibilityResponse(BaseModel):
    """A decision, its explanation, and a traceable policy reference."""

    model_config = ConfigDict(extra="forbid")
    order_id: str
    eligible: bool
    reason_code: str
    reason: str
    policy_reference: str
    evaluated_on: date


def utc_today() -> date:
    """Use UTC consistently for calendar-day policy calculations."""
    return datetime.now(UTC).date()


def create_app(*, api_key: str | None = None, clock: Callable[[], date] = utc_today) -> FastAPI:
    """Compose the demo; fail closed if an API credential was not configured."""
    configured_key = api_key if api_key is not None else os.environ.get("AURORA_API_KEY", "")
    if len(configured_key.strip()) < 32:
        raise ValueError("Set AURORA_API_KEY to a random key of at least 32 characters.")

    orders = demo_orders(clock())
    header = APIKeyHeader(name="X-API-Key", auto_error=False)
    app = FastAPI(title="Aurora Orders Demo", version="0.1.0")

    def authenticate(key: Annotated[str | None, Security(header)]) -> None:
        if key is None or not secrets.compare_digest(key.encode(), configured_key.encode()):
            raise HTTPException(status_code=401, detail="Invalid integration credential.")

    def authorized_order(order_id: str) -> Order:
        try:
            return find_order(orders, order_id=order_id, customer_ref=DEMO_CUSTOMER_REF)
        except OrderUnavailable as error:
            raise HTTPException(status_code=404, detail="Order unavailable.") from error

    @app.get("/health", include_in_schema=False)
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get(
        "/orders/{order_id}",
        operation_id="getOrder",
        response_model=OrderResponse,
        dependencies=[Depends(authenticate)],
    )
    def get_order(order_id: OrderId) -> OrderResponse:
        order = authorized_order(order_id)
        return OrderResponse(order_id=order.order_id, product=order.product, status=order.status)

    @app.get(
        "/orders/{order_id}/return-eligibility",
        operation_id="checkReturnEligibility",
        response_model=EligibilityResponse,
        dependencies=[Depends(authenticate)],
    )
    def get_eligibility(order_id: OrderId) -> EligibilityResponse:
        order = authorized_order(order_id)
        today = clock()
        decision = evaluate_return(order, today=today)
        return EligibilityResponse(
            order_id=order.order_id,
            eligible=decision.eligible,
            reason_code=decision.reason_code,
            reason=decision.reason,
            policy_reference=decision.policy_reference,
            evaluated_on=today,
        )

    return app
