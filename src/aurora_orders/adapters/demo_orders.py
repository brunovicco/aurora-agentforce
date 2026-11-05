"""Relative dates make the demo repeatable on each application startup."""

from datetime import date, timedelta

from aurora_orders.domain.policy import Order

DEMO_CUSTOMER_REF = "customer-demo-001"


def demo_orders(today: date) -> tuple[Order, ...]:
    """Build only synthetic records, including one inaccessible customer's order."""
    return (
        Order("AUR-1001", DEMO_CUSTOMER_REF, "Fone Aurora", "delivered", today - timedelta(days=5)),
        Order(
            "AUR-1002", DEMO_CUSTOMER_REF, "Teclado Aurora", "delivered", today - timedelta(days=31)
        ),
        Order("AUR-1003", DEMO_CUSTOMER_REF, "Mouse Aurora", "shipped"),
        Order(
            "AUR-1004", DEMO_CUSTOMER_REF, "Capa Aurora", "delivered", today - timedelta(days=30)
        ),
        Order(
            "AUR-1005",
            DEMO_CUSTOMER_REF,
            "Item personalizado",
            "delivered",
            today,
            returnable=False,
        ),
        Order("AUR-1006", DEMO_CUSTOMER_REF, "Suporte Aurora", "cancelled"),
        Order("AUR-9001", "customer-demo-002", "Pedido privado de teste", "delivered", today),
    )
