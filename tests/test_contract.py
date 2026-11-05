import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from jsonschema import Draft4Validator
from openapi_spec_validator import validate

CONTRACT = json.loads((Path(__file__).parents[1] / "salesforce" / "openapi.json").read_text())


def test_salesforce_contract_is_valid_openapi_30() -> None:
    validate(CONTRACT)
    assert CONTRACT["openapi"] == "3.0.3"


@pytest.mark.parametrize("path", list(CONTRACT["paths"]))
def test_operation_names_and_paths_match_running_api(client: TestClient, path: str) -> None:
    live = client.get("/openapi.json").json()
    assert (
        live["paths"][path]["get"]["operationId"] == CONTRACT["paths"][path]["get"]["operationId"]
    )


@pytest.mark.parametrize("path", list(CONTRACT["paths"]))
@pytest.mark.parametrize(
    ("order_id", "authenticated", "status"),
    [
        ("AUR-1001", True, 200),
        ("AUR-1002", True, 200),
        ("AUR-1001", False, 401),
        ("AUR-9999", True, 404),
        ("AUR-9001", True, 404),
        ("invalid", True, 422),
    ],
)
def test_actual_responses_follow_salesforce_contract(
    client: TestClient,
    headers: dict[str, str],
    path: str,
    order_id: str,
    authenticated: bool,
    status: int,
) -> None:
    response = client.get(
        path.replace("{order_id}", order_id), headers=headers if authenticated else {}
    )
    assert response.status_code == status
    schema = CONTRACT["paths"][path]["get"]["responses"][str(status)]["content"][
        "application/json"
    ]["schema"]
    Draft4Validator(schema).validate(response.json())
