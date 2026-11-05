from datetime import date, timedelta

import pytest

from aurora_orders.domain.policy import Order, OrderStatus, evaluate_return

TODAY = date(2026, 11, 5)


@pytest.mark.parametrize(
    ("elapsed_days", "eligible", "code"),
    [
        (0, True, "ELIGIBLE"),
        (29, True, "ELIGIBLE"),
        (30, True, "ELIGIBLE"),
        (31, False, "WINDOW_EXPIRED"),
        (-1, False, "INVALID_DELIVERY_DATE"),
    ],
)
def test_return_window_is_inclusive(elapsed_days: int, eligible: bool, code: str) -> None:
    order = Order("AUR-1001", "demo", "Fone", "delivered", TODAY - timedelta(days=elapsed_days))
    decision = evaluate_return(order, today=TODAY)
    assert decision.eligible is eligible
    assert decision.reason_code == code
    assert decision.policy_reference == "AURORA-DEMO-RETURNS-v1"


@pytest.mark.parametrize("status", ["processing", "shipped", "cancelled"])
def test_non_delivered_orders_are_ineligible(status: OrderStatus) -> None:
    decision = evaluate_return(Order("AUR-1001", "demo", "Fone", status), today=TODAY)
    assert decision.eligible is False
    assert decision.reason_code == "NOT_DELIVERED"


def test_missing_delivery_date_requires_review() -> None:
    decision = evaluate_return(Order("AUR-1001", "demo", "Fone", "delivered"), today=TODAY)
    assert decision.eligible is False
    assert decision.reason_code == "INVALID_DELIVERY_DATE"


def test_excluded_item_is_ineligible_even_on_delivery_day() -> None:
    order = Order("AUR-1001", "demo", "Personalizado", "delivered", TODAY, returnable=False)
    decision = evaluate_return(order, today=TODAY)
    assert decision.eligible is False
    assert decision.reason_code == "EXCLUDED_ITEM"
