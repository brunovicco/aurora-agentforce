from collections.abc import Generator
from datetime import UTC, date, datetime

import pytest
from fastapi.testclient import TestClient

from aurora_orders.entrypoints.api import create_app

TEST_API_KEY = "synthetic-test-credential-not-a-secret-0001"
TEST_SESSION_KEY = "synthetic-different-customer-signing-key-for-tests-0001"
TODAY = date(2026, 11, 5)
NOW = datetime(2026, 11, 5, 12, 0, tzinfo=UTC)


@pytest.fixture
def client() -> Generator[TestClient]:
    # Preserve the existing Salesforce demo contract tests in explicitly unsafe mode.
    with TestClient(
        create_app(
            api_key=TEST_API_KEY,
            clock=lambda: TODAY,
            session_clock=lambda: NOW,
            session_signing_key=TEST_SESSION_KEY,
            allow_unverified_demo_reads=True,
        )
    ) as test_client:
        yield test_client


@pytest.fixture
def headers() -> dict[str, str]:
    return {"X-API-Key": TEST_API_KEY}
