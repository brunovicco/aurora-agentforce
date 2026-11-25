"""Regression tests for the manual evidence scoring contract."""

import json
from typing import Any

import pytest
from scripts.portal_runtime_eval import SCENARIOS, evaluate


def inputs() -> tuple[dict[str, Any], dict[str, Any]]:
    plan = json.loads(SCENARIOS.read_text())
    evidence = {
        "schema_version": 1,
        "environment": "isolated_development",
        "candidate_commit": "a" * 40,
        "observations": [
            {
                "id": case["id"],
                "observed": case["expected"],
                "data_disclosed": False,
                "mutations": 0,
                "evidence_ref": f"EV-{i:03}",
            }
            for i, case in enumerate(plan["cases"], 1)
        ],
    }
    return plan, evidence


def test_all_reported_pass_does_not_authorize_activation() -> None:
    plan, evidence = inputs()
    result = evaluate(plan, evidence)
    assert result["counts"] == {"pass": 15, "fail": 0, "not_run": 0}
    assert result["all_reported_checks_pass"] is True
    assert result["independently_verified"] is False
    assert result["activation_authorized"] is False


@pytest.mark.parametrize(
    ("key", "value"),
    [("observed", "unexpected"), ("data_disclosed", True), ("mutations", 1)],
)
def test_failed_observation(key: str, value: Any) -> None:
    plan, evidence = inputs()
    evidence["observations"][0][key] = value
    result = evaluate(plan, evidence)
    assert result["counts"]["fail"] == 1
    assert result["all_reported_checks_pass"] is False


def test_missing_observation_is_not_run() -> None:
    plan, evidence = inputs()
    evidence["observations"].pop()
    assert evaluate(plan, evidence)["counts"]["not_run"] == 1


def test_duplicate_observation_rejected() -> None:
    plan, evidence = inputs()
    evidence["observations"].append(evidence["observations"][0])
    with pytest.raises(ValueError, match="duplicate"):
        evaluate(plan, evidence)


def test_invalid_commit_rejected() -> None:
    plan, evidence = inputs()
    evidence["candidate_commit"] = "main"
    with pytest.raises(ValueError, match="commit"):
        evaluate(plan, evidence)


def test_unexecuted_evidence_rejected() -> None:
    plan, evidence = inputs()
    evidence["observations"][0]["observed"] = "not_run"
    with pytest.raises(ValueError, match="Unexecuted"):
        evaluate(plan, evidence)
