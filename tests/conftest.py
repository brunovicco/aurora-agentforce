from collections.abc import Generator
from datetime import date

import pytest
from fastapi.testclient import TestClient

from aurora_orders.entrypoints.api import create_app

TEST_API_KEY = "synthetic-test-credential-not-a-secret-0001"
TODAY = date(2026, 11, 5)


@pytest.fixture
def client() -> Generator[TestClient]:
    with TestClient(create_app(api_key=TEST_API_KEY, clock=lambda: TODAY)) as test_client:
        yield test_client


@pytest.fixture
def headers() -> dict[str, str]:
    return {"X-API-Key": TEST_API_KEY}
