#!/usr/bin/env python3
"""Mint a short-lived *synthetic* customer token for isolated local demos only.

This tool does not authenticate a real person. Never run it as a public service.
"""

import argparse
import os
import secrets
from datetime import UTC, datetime

from aurora_orders.application.customer_sessions import mint_demo_session


def main() -> None:
    """Print one synthetic test token; do not log it in an application."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--customer",
        choices=("customer-demo-001", "customer-demo-002"),
        required=True,
    )
    args = parser.parse_args()
    signing_key = os.environ.get("AURORA_CUSTOMER_SESSION_SECRET", "")
    print(  # noqa: T201 - explicit stdout-only demo token issuance
        mint_demo_session(
            signing_key=signing_key,
            customer_ref=args.customer,
            session_id=secrets.token_urlsafe(18),
            now=datetime.now(UTC),
        )
    )


if __name__ == "__main__":
    main()
