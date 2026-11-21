#!/usr/bin/env python3
"""Static fail-closed checks for Aurora's Salesforce Flow metadata.

These checks complement, but do not replace, Salesforce validation and runtime tests.
"""

import sys
from collections import deque
from pathlib import Path
from xml.etree import ElementTree as ET

# This script uses assertions intentionally to validate trusted repository metadata.
# ruff: noqa: S101

NAMESPACE = "http://soap.sforce.com/2006/04/metadata"
NODE_TYPES = {
    "actionCalls",
    "assignments",
    "decisions",
    "recordCreates",
    "recordLookups",
    "ends",
}


def tag(name: str) -> str:
    """Return a qualified Salesforce metadata tag."""
    return f"{{{NAMESPACE}}}{name}"


def verify(flow_path: Path) -> None:
    """Verify that every Case read/write path is gated by trusted approval."""
    root = ET.parse(flow_path).getroot()  # noqa: S314 - trusted local repository metadata
    assert root.tag == tag("Flow")
    assert root.findtext(tag("status")) in {"Active", "Draft"}, "Unexpected Flow status"
    assert root.findtext(tag("runInMode")) == "UserMode", "Enforce user permissions"

    nodes = {
        child.findtext(tag("name")): child
        for child in root
        if child.tag.removeprefix(f"{{{NAMESPACE}}}") in NODE_TYPES
    }
    expected_count = sum(child.tag.removeprefix(f"{{{NAMESPACE}}}") in NODE_TYPES for child in root)
    assert len(nodes) == expected_count, "Duplicate node names"
    graph = {
        name: [reference.text for reference in node.iter(tag("targetReference"))]
        for name, node in nodes.items()
    }
    for source, targets in graph.items():
        for target in targets:
            assert target in nodes, f"Broken connector: {source} -> {target}"

    creation_nodes = root.findall(tag("recordCreates"))
    assert len(creation_nodes) == 1, "Exactly one controlled Case create"
    creation = creation_nodes[0]
    assert creation.findtext(tag("object")) == "Case"
    fault_target = creation.findtext(f"{tag('faultConnector')}/{tag('targetReference')}")
    assert fault_target == "GetCaseAfterCreateFailure"
    assignments = {
        assignment.findtext(tag("field")): (
            assignment.findtext(f"{tag('value')}/{tag('elementReference')}")
            or assignment.findtext(f"{tag('value')}/{tag('stringValue')}")
        )
        for assignment in creation.findall(tag("inputAssignments"))
    }
    assert assignments["AuroraRequestKey__c"] == "frmRequestKey"
    assert assignments["Subject"] == "frmCaseSubject"
    assert assignments["Origin"] == "Web"
    assert assignments["Status"] == "New"
    assert "OwnerId" not in assignments and "ContactId" not in assignments

    input_vars = [
        item.findtext(tag("name"))
        for item in root.findall(tag("variables"))
        if item.findtext(tag("isInput")) == "true"
    ]
    output_vars = [
        item.findtext(tag("name"))
        for item in root.findall(tag("variables"))
        if item.findtext(tag("isOutput")) == "true"
    ]
    assert input_vars == ["order_id"], input_vars
    assert set(output_vars) == {"outcome", "case_number"}, output_vars

    def reachable(start: str, connections: dict) -> set[str]:
        seen = {start}
        queue = deque([start])
        while queue:
            for target in connections.get(queue.popleft(), []):
                if target not in seen:
                    seen.add(target)
                    queue.append(target)
        return seen

    assert set(graph["CaseAlreadyExists"]) == {
        "ReturnExisting",
        "CreateAuroraSupportCase",
    }, graph["CaseAlreadyExists"]
    assert graph["StoreValidatedOrder"] == ["FindApprovedAuroraRequest"]

    approval_lookup = nodes["FindApprovedAuroraRequest"]
    assert approval_lookup.findtext(tag("object")) == "AuroraCaseApproval__c"
    filters = {
        item.findtext(tag("field")): (
            item.findtext(tag("operator")),
            item.findtext(f"{tag('value')}/{tag('elementReference')}")
            or item.findtext(f"{tag('value')}/{tag('booleanValue')}"),
        )
        for item in approval_lookup.findall(tag("filters"))
    }
    assert filters == {
        "RequestKey__c": ("EqualTo", "frmRequestKey"),
        "Approved__c": ("EqualTo", "true"),
        "ExpiresAt__c": ("GreaterThan", "$Flow.CurrentDateTime"),
    }, filters
    assert set(graph["ApprovalExists"]) == {
        "ReturnApprovalRequired",
        "FindExistingAuroraCase",
    }

    # Disconnect the approval-success branch: protected operations must be unreachable.
    disconnected = {key: list(targets) for key, targets in graph.items()}
    disconnected["ApprovalExists"] = ["ReturnApprovalRequired"]
    protected_nodes = (
        "FindExistingAuroraCase",
        "GetCreatedCase",
        "GetCaseAfterCreateFailure",
        "CreateAuroraSupportCase",
        "ReturnExisting",
        "ReturnConcurrentExisting",
    )
    for protected in protected_nodes:
        assert protected not in reachable("ValidateAuroraOrder", disconnected), protected

    assert "CreateAuroraSupportCase" not in reachable("ReturnApprovalRequired", graph)
    assert "CreateAuroraSupportCase" in reachable("ApprovalExists", graph)
    for rejected in ("HandleInvalidOrder", "HandleOrderLookupFailure", "ReturnFailed"):
        assert "CreateAuroraSupportCase" not in reachable(rejected, graph), rejected
    assert "FindApprovedAuroraRequest" in reachable("StoreValidatedOrder", graph)
    assert "ReturnCreated" in reachable("GetCreatedCase", graph)

    request_key = root.find(f"{tag('formulas')}[{tag('name')}='frmRequestKey']")
    assert request_key is not None
    assert "customer-demo-001:" in (request_key.findtext(tag("expression")) or "")

    print(f"PASS: static Flow metadata and authorization graph ({len(nodes)} nodes).")
    print("NOTE: Salesforce Metadata API validation and live-action tests remain separate.")


if __name__ == "__main__":
    default = Path("salesforce/force-app/main/default/flows/AbrirCasoPosVenda.flow-meta.xml")
    verify(Path(sys.argv[1]) if len(sys.argv) > 1 else default)
