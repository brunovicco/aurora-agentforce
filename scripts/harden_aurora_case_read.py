#!/usr/bin/env python3
"""Rewire an older Aurora Flow so existing-Case reads require approval.

This historical maintenance tool validates the candidate graph before changing
the local metadata file. It never deploys to a Salesforce org.
"""

from pathlib import Path
from tempfile import NamedTemporaryFile
from xml.etree import ElementTree as ET

from verify_aurora_flow import verify

FLOW_PATH = Path("salesforce/force-app/main/default/flows/AbrirCasoPosVenda.flow-meta.xml")
NAMESPACE = "http://soap.sforce.com/2006/04/metadata"


def tag(name: str) -> str:
    """Return a qualified Salesforce metadata tag."""
    return f"{{{NAMESPACE}}}{name}"


def one_node(root: ET.Element, kind: str, name: str) -> ET.Element:
    """Return one named Flow node, rejecting missing or duplicate matches."""
    matches = [
        node
        for node in root.findall(tag(kind))
        if node.findtext(tag("name")) == name
    ]
    if len(matches) != 1:
        raise ValueError(f"Expected exactly one {kind} named {name}; found {len(matches)}")
    return matches[0]


def connector_target(element: ET.Element, connection: str) -> ET.Element:
    """Return a connector's target reference."""
    reference = element.find(f"{tag(connection)}/{tag('targetReference')}")
    if reference is None:
        name = element.findtext(tag("name"))
        raise ValueError(f"Missing connector {connection} on {name}")
    return reference


def main() -> None:
    """Apply the graph fix only to a verified legacy layout."""
    if not FLOW_PATH.is_file():
        raise SystemExit("Run from the repository root: Flow metadata not found.")

    tree = ET.parse(FLOW_PATH)  # noqa: S314 - trusted repository metadata
    root = tree.getroot()
    if root.tag != tag("Flow") or root.findtext(tag("runInMode")) != "UserMode":
        raise SystemExit("Unexpected Flow or execution mode; no changes applied.")

    store = one_node(root, "assignments", "StoreValidatedOrder")
    case_decision = one_node(root, "decisions", "CaseAlreadyExists")
    approval_decision = one_node(root, "decisions", "ApprovalExists")
    approved_rule = [
        rule
        for rule in approval_decision.findall(tag("rules"))
        if rule.findtext(tag("name")) == "ApprovedRequest"
    ]
    if len(approved_rule) != 1:
        raise SystemExit("ApprovedRequest rule is missing or duplicated.")

    routes = {
        "after_validation": connector_target(store, "connector"),
        "no_existing_case": connector_target(case_decision, "defaultConnector"),
        "approved": connector_target(approved_rule[0], "connector"),
    }
    legacy = {
        "after_validation": "FindExistingAuroraCase",
        "no_existing_case": "FindApprovedAuroraRequest",
        "approved": "CreateAuroraSupportCase",
    }
    protected = {
        "after_validation": "FindApprovedAuroraRequest",
        "no_existing_case": "CreateAuroraSupportCase",
        "approved": "FindExistingAuroraCase",
    }
    actual = {key: reference.text for key, reference in routes.items()}
    if actual == protected:
        verify(FLOW_PATH)
        print("PASS: approval-first graph is already protected; no changes needed.")
        return
    if actual != legacy:
        raise SystemExit(f"Unexpected Flow connections; no changes applied: {actual}")

    for key, reference in routes.items():
        reference.text = protected[key]

    ET.register_namespace("", NAMESPACE)
    ET.indent(tree, space="  ")
    with NamedTemporaryFile(
        mode="wb",
        prefix="aurora-flow-",
        suffix=".xml",
        dir=FLOW_PATH.parent,
        delete=False,
    ) as output:
        candidate = Path(output.name)
        tree.write(output, encoding="utf-8", xml_declaration=True)
    try:
        verify(candidate)
        candidate.replace(FLOW_PATH)
    finally:
        candidate.unlink(missing_ok=True)
    print("PASS: Flow approval guard repaired after validation of the candidate graph.")


if __name__ == "__main__":
    main()
