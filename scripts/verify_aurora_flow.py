#!/usr/bin/env python3
"""Static fail-closed checks for Aurora's Salesforce Flow metadata.

This does not replace Salesforce Metadata API validation or runtime tests.
"""

from __future__ import annotations

from collections import deque
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

NAMESPACE = "http://soap.sforce.com/2006/04/metadata"
TAG = lambda name: f"{{{NAMESPACE}}}{name}"
NODE_TYPES = {"actionCalls", "assignments", "decisions", "recordCreates", "recordLookups", "ends"}


def verify(flow_path: Path) -> None:
    root = ET.parse(flow_path).getroot()
    assert root.tag == TAG("Flow")
    assert root.findtext(TAG("status")) in {"Active", "Draft"}, "Unexpected Flow status"
    assert root.findtext(TAG("runInMode")) == "UserMode", "Enforce user permissions"

    nodes = {
        child.findtext(TAG("name")): child
        for child in root
        if child.tag.removeprefix("{" + NAMESPACE + "}") in NODE_TYPES
    }
    assert len(nodes) == sum(
        c.tag.removeprefix("{" + NAMESPACE + "}") in NODE_TYPES for c in root
    ), "Duplicate node names"
    graph = {
        name: [x.text for x in node.iter(TAG("targetReference"))]
        for name, node in nodes.items()
    }
    for source, targets in graph.items():
        for target in targets:
            assert target in nodes, f"Broken connector: {source} -> {target}"

    creation_nodes = [x for x in root.findall(TAG("recordCreates"))]
    assert len(creation_nodes) == 1, "Exactly one controlled Case create"
    creation = creation_nodes[0]
    assert creation.findtext(TAG("object")) == "Case"
    assert creation.findtext(TAG("faultConnector") + "/" + TAG("targetReference")) == "GetCaseAfterCreateFailure"
    assignments = {
        a.findtext(TAG("field")): a.findtext(TAG("value") + "/" + TAG("elementReference")) or
        a.findtext(TAG("value") + "/" + TAG("stringValue"))
        for a in creation.findall(TAG("inputAssignments"))
    }
    assert assignments["AuroraRequestKey__c"] == "frmRequestKey"
    assert assignments["Subject"] == "frmCaseSubject"
    assert assignments["Origin"] == "Web"
    assert assignments["Status"] == "New"
    assert "OwnerId" not in assignments and "ContactId" not in assignments

    input_vars = [x.findtext(TAG("name")) for x in root.findall(TAG("variables"))
                  if x.findtext(TAG("isInput")) == "true"]
    output_vars = [x.findtext(TAG("name")) for x in root.findall(TAG("variables"))
                   if x.findtext(TAG("isOutput")) == "true"]
    assert input_vars == ["order_id"], input_vars
    assert set(output_vars) == {"outcome", "case_number"}, output_vars

    def reachable(start: str) -> set[str]:
        seen = {start}
        queue = deque([start])
        while queue:
            for target in graph.get(queue.popleft(), []):
                if target not in seen:
                    seen.add(target)
                    queue.append(target)
        return seen

    # Authorization is enforced in Flow, independent from Agent Script or model output.
    assert set(graph["CaseAlreadyExists"]) == {"ReturnExisting", "CreateAuroraSupportCase"}, graph["CaseAlreadyExists"]
    assert graph["StoreValidatedOrder"] == ["FindApprovedAuroraRequest"]
    approval_lookup = nodes["FindApprovedAuroraRequest"]
    assert approval_lookup.findtext(TAG("object")) == "AuroraCaseApproval__c"
    filters = {
        f.findtext(TAG("field")): (f.findtext(TAG("operator")),
            f.findtext(TAG("value") + "/" + TAG("elementReference")) or
            f.findtext(TAG("value") + "/" + TAG("booleanValue")))
        for f in approval_lookup.findall(TAG("filters"))
    }
    assert filters == {
        "RequestKey__c": ("EqualTo", "frmRequestKey"),
        "Approved__c": ("EqualTo", "true"),
        "ExpiresAt__c": ("GreaterThan", "$Flow.CurrentDateTime"),
    }, filters
    assert set(graph["ApprovalExists"]) == {"ReturnApprovalRequired", "FindExistingAuroraCase"}
    # Remove the approval gate from graph; creation must become unreachable.
    disconnected = {k:list(v) for k,v in graph.items()}
    disconnected["ApprovalExists"] = ["ReturnApprovalRequired"]
    def reachable_disconnected(start: str) -> set[str]:
        seen={start}; pending=[start]
        while pending:
            for target in disconnected.get(pending.pop(),[]):
                if target not in seen:
                    seen.add(target);pending.append(target)
        return seen
    assert "CreateAuroraSupportCase" not in reachable_disconnected("ValidateAuroraOrder")
    # Authorization must dominate every path that reads or creates Case records.
    for protected in (
        "FindExistingAuroraCase", "GetCreatedCase", "GetCaseAfterCreateFailure",
        "CreateAuroraSupportCase", "ReturnExisting", "ReturnConcurrentExisting",
    ):
        assert protected not in reachable_disconnected("ValidateAuroraOrder"), protected
    assert "CreateAuroraSupportCase" not in reachable("ReturnApprovalRequired")
    assert "CreateAuroraSupportCase" in reachable("ApprovalExists")

    # Reject any path from API failures or invalid orders to the record creation node.
    for rejected in ("HandleInvalidOrder", "HandleOrderLookupFailure", "ReturnFailed"):
        assert "CreateAuroraSupportCase" not in reachable(rejected), rejected
    assert "FindApprovedAuroraRequest" in reachable("StoreValidatedOrder")
    assert "ReturnCreated" in reachable("GetCreatedCase")

    key = root.find(f"{TAG('formulas')}[{TAG('name')}='frmRequestKey']")
    assert key is not None
    assert "customer-demo-001:" in (key.findtext(TAG("expression")) or "")

    print(f"PASS: static XML/graph checks ({len(nodes)} nodes).")
    print("NOTE: Salesforce Metadata API dry-run and runtime tests are still required.")


if __name__ == "__main__":
    default = Path("salesforce/force-app/main/default/flows/AbrirCasoPosVenda.flow-meta.xml")
    verify(Path(sys.argv[1]) if len(sys.argv) > 1 else default)
