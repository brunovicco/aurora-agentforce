"""Relative dates make the demo repeatable on each application startup."""

from datetime import date, timedelta

from aurora_orders.domain.policy import Order

DEMO_CUSTOMER_REF = "customer-demo-001"


def demo_orders(today: date) -> tuple[Order, ...]:
    """Build only synthetic records, including one inaccessible customer's order."""
    return (
        Order(
            "AUR-1001",
            DEMO_CUSTOMER_REF,
            "Aurora Headphones",
            "delivered",
            today - timedelta(days=5),
        ),
        Order(
            "AUR-1002",
            DEMO_CUSTOMER_REF,
            "Aurora Keyboard",
            "delivered",
            today - timedelta(days=31),
        ),
        Order("AUR-1003", DEMO_CUSTOMER_REF, "Aurora Mouse", "shipped"),
        Order(
            "AUR-1004", DEMO_CUSTOMER_REF, "Aurora Cover", "delivered", today - timedelta(days=30)
        ),
        Order(
            "AUR-1005",
            DEMO_CUSTOMER_REF,
            "Custom Item",
            "delivered",
            today,
            returnable=False,
        ),
        Order("AUR-1006", DEMO_CUSTOMER_REF, "Aurora Stand", "cancelled"),
        Order("AUR-9001", "customer-demo-002", "Private Test Order", "delivered", today),
    )
