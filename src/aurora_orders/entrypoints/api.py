"""HTTP order reads with separate integration and customer authorization boundaries."""

import os
import secrets
from collections.abc import Callable
from datetime import UTC, date, datetime
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Path, Security
from fastapi.security import APIKeyHeader
from pydantic import BaseModel, ConfigDict

from aurora_orders.adapters.demo_orders import DEMO_CUSTOMER_REF, demo_orders
from aurora_orders.application.customer_sessions import (
    InvalidCustomerSession,
    VerifiedCustomer,
    validate_signing_key,
    verify_customer_session,
)
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


def utc_now() -> datetime:
    """Use an aware UTC clock when checking customer-session expiry."""
    return datetime.now(UTC)


def create_app(
    *,
    api_key: str | None = None,
    clock: Callable[[], date] = utc_today,
    session_clock: Callable[[], datetime] = utc_now,
    session_signing_key: str | None = None,
    revoked_session_ids: frozenset[str] = frozenset(),
    allow_unverified_demo_reads: bool | None = None,
) -> FastAPI:
    """Compose the demo; unverified legacy reads are disabled unless opted in."""
    configured_key = api_key if api_key is not None else os.environ.get("AURORA_API_KEY", "")
    if len(configured_key.strip()) < 32:
        raise ValueError("Set AURORA_API_KEY to a random key of at least 32 characters.")
    session_secret = (
        session_signing_key
        if session_signing_key is not None
        else os.environ.get("AURORA_CUSTOMER_SESSION_SECRET", "")
    )
    if session_secret:
        validate_signing_key(session_secret)
        if secrets.compare_digest(session_secret.encode(), configured_key.encode()):
            raise ValueError("Use different secrets for integration and customer sessions.")
    unsafe_demo = (
        os.environ.get("AURORA_ENABLE_UNVERIFIED_DEMO_READS") == "1"
        if allow_unverified_demo_reads is None
        else allow_unverified_demo_reads
    )

    orders = demo_orders(clock())
    integration_header = APIKeyHeader(name="X-API-Key", auto_error=False)
    customer_header = APIKeyHeader(name="X-Aurora-Customer-Session", auto_error=False)
    app = FastAPI(title="Aurora Orders Demo", version="0.2.0")

    def authenticate(key: Annotated[str | None, Security(integration_header)]) -> None:
        if key is None or not secrets.compare_digest(key.encode(), configured_key.encode()):
            raise HTTPException(status_code=401, detail="Invalid integration credential.")

    def verified_customer(
        token: Annotated[str | None, Security(customer_header)],
    ) -> VerifiedCustomer:
        if not session_secret:
            raise HTTPException(status_code=503, detail="Verified customer reads unavailable.")
        if token is None:
            raise HTTPException(status_code=401, detail="Invalid customer session.")
        try:
            return verify_customer_session(
                token,
                signing_key=session_secret,
                now=session_clock(),
                revoked_session_ids=revoked_session_ids,
            )
        except InvalidCustomerSession as error:
            raise HTTPException(status_code=401, detail="Invalid customer session.") from error

    def allow_legacy() -> None:
        if not unsafe_demo:
            raise HTTPException(status_code=403, detail="Unverified demo reads are disabled.")

    def authorized_order(order_id: str, *, customer_ref: str) -> Order:
        try:
            return find_order(orders, order_id=order_id, customer_ref=customer_ref)
        except OrderUnavailable as error:
            raise HTTPException(status_code=404, detail="Order unavailable.") from error

    def order_response(order: Order) -> OrderResponse:
        return OrderResponse(order_id=order.order_id, product=order.product, status=order.status)

    def eligibility_response(order: Order) -> EligibilityResponse:
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

    @app.get("/health", include_in_schema=False)
    def health() -> dict[str, str]:
        return {"status": "ok"}

    # Existing Salesforce actions use these routes. Enable only for an isolated demo.
    @app.get(
        "/orders/{order_id}",
        operation_id="getOrder",
        response_model=OrderResponse,
        dependencies=[Depends(authenticate), Depends(allow_legacy)],
    )
    def get_order(order_id: OrderId) -> OrderResponse:
        return order_response(authorized_order(order_id, customer_ref=DEMO_CUSTOMER_REF))

    @app.get(
        "/orders/{order_id}/return-eligibility",
        operation_id="checkReturnEligibility",
        response_model=EligibilityResponse,
        dependencies=[Depends(authenticate), Depends(allow_legacy)],
    )
    def get_eligibility(order_id: OrderId) -> EligibilityResponse:
        return eligibility_response(authorized_order(order_id, customer_ref=DEMO_CUSTOMER_REF))

    # The session must be minted and injected by trusted infrastructure, never the LLM.
    @app.get(
        "/verified/orders/{order_id}",
        operation_id="getVerifiedOrder",
        response_model=OrderResponse,
        dependencies=[Depends(authenticate)],
    )
    def get_verified_order(
        order_id: OrderId,
        customer: Annotated[VerifiedCustomer, Depends(verified_customer)],
    ) -> OrderResponse:
        return order_response(authorized_order(order_id, customer_ref=customer.customer_ref))

    @app.get(
        "/verified/orders/{order_id}/return-eligibility",
        operation_id="checkVerifiedReturnEligibility",
        response_model=EligibilityResponse,
        dependencies=[Depends(authenticate)],
    )
    def get_verified_eligibility(
        order_id: OrderId,
        customer: Annotated[VerifiedCustomer, Depends(verified_customer)],
    ) -> EligibilityResponse:
        return eligibility_response(authorized_order(order_id, customer_ref=customer.customer_ref))

    return app
