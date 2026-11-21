#!/usr/bin/env python3
"""Rewire the Aurora Flow so all existing-Case reads require trusted approval.

Expected input: current Salesforce Flow metadata from aurora-approval-guard-patch.
Does not deploy. Fails closed if unexpected graph shape is detected.
"""
from pathlib import Path
from xml.etree import ElementTree as ET

FLOW_PATH = Path('salesforce/force-app/main/default/flows/AbrirCasoPosVenda.flow-meta.xml')
VERIFY_PATH = Path('scripts/verify_aurora_flow.py')
NS = 'http://soap.sforce.com/2006/04/metadata'
Q = lambda tag: f'{{{NS}}}{tag}'

if not FLOW_PATH.exists() or not VERIFY_PATH.exists():
    raise SystemExit('Run this from the aurora-agentforce root: Flow/verifier files were not found.')

tree = ET.parse(FLOW_PATH)
root = tree.getroot()
if root.tag != Q('Flow') or root.findtext(Q('runInMode')) != 'UserMode':
    raise SystemExit('Unexpected Flow or execution mode other than UserMode. No changes applied.')

def node(kind, name):
    matches = [e for e in root.findall(Q(kind)) if e.findtext(Q('name')) == name]
    if len(matches) != 1:
        raise SystemExit(f'Expected exactly one {kind} named {name}; found {len(matches)}')
    return matches[0]

store = node('assignments', 'StoreValidatedOrder')
case_decision = node('decisions', 'CaseAlreadyExists')
approval_decision = node('decisions', 'ApprovalExists')
approved_rule = [r for r in approval_decision.findall(Q('rules')) if r.findtext(Q('name')) == 'ApprovedRequest']
if len(approved_rule) != 1:
    raise SystemExit('ApprovedRequest rule is missing or duplicated')

def connector_target(element, connection):
    ref = element.find(f'{Q(connection)}/{Q("targetReference")}')
    if ref is None:
        raise SystemExit(f'Connector {connection} missing from element {element.findtext(Q("name"))}')
    return ref

routes = {
    'after_validation': connector_target(store, 'connector'),
    'no_existing_case': connector_target(case_decision, 'defaultConnector'),
    'approved': connector_target(approved_rule[0], 'connector'),
}
old = {
    'after_validation': 'FindExistingAuroraCase',
    'no_existing_case': 'FindApprovedAuroraRequest',
    'approved': 'CreateAuroraSupportCase',
}
new = {
    'after_validation': 'FindApprovedAuroraRequest',
    'no_existing_case': 'CreateAuroraSupportCase',
    'approved': 'FindExistingAuroraCase',
}
actual = {key: element.text for key, element in routes.items()}
if actual not in (old, new):
    raise SystemExit(f'Flow has unexpected connections; no changes applied: {actual}')

verifier = VERIFY_PATH.read_text(encoding='utf-8')
assert_old_case = 'assert set(graph["CaseAlreadyExists"]) == {"ReturnExisting", "FindApprovedAuroraRequest"}, graph["CaseAlreadyExists"]'
assert_new_case = 'assert set(graph["CaseAlreadyExists"]) == {"ReturnExisting", "CreateAuroraSupportCase"}, graph["CaseAlreadyExists"]'
assert_old_approval = 'assert set(graph["ApprovalExists"]) == {"ReturnApprovalRequired", "CreateAuroraSupportCase"}'
assert_new_approval = 'assert set(graph["ApprovalExists"]) == {"ReturnApprovalRequired", "FindExistingAuroraCase"}'
assert_anchor = '    assert "CreateAuroraSupportCase" not in reachable_disconnected("ValidateAuroraOrder")'
protected_check = '''    # Authorization must dominate every path that reads or creates Case records.
    for protected in (
        "FindExistingAuroraCase", "GetCreatedCase", "GetCaseAfterCreateFailure",
        "CreateAuroraSupportCase", "ReturnExisting", "ReturnConcurrentExisting",
    ):
        assert protected not in reachable_disconnected("ValidateAuroraOrder"), protected
'''

if actual == old:
    for string in (assert_old_case, assert_old_approval, assert_anchor):
        if verifier.count(string) != 1:
            raise SystemExit(f'Unexpected verifier: expected exactly one occurrence of: {string}')
    verifier = verifier.replace(assert_old_case, assert_new_case)
    verifier = verifier.replace(assert_old_approval, assert_new_approval)
    verifier = verifier.replace(assert_anchor, assert_anchor + '\n' + protected_check.rstrip('\n'))
    verifier = verifier.replace(
        '    approval_lookup = nodes["FindApprovedAuroraRequest"]',
        '    assert graph["StoreValidatedOrder"] == ["FindApprovedAuroraRequest"]\n'
        '    approval_lookup = nodes["FindApprovedAuroraRequest"]'
    )
    for key, element in routes.items():
        element.text = new[key]
    ET.register_namespace('', NS)
    ET.indent(tree, space='  ')
    tree.write(FLOW_PATH, encoding='utf-8', xml_declaration=True)
    VERIFY_PATH.write_text(verifier, encoding='utf-8')
    print('PASS: Flow secured and verifier updated (3 connectors changed).')
else:
    for string in (assert_new_case, assert_new_approval, protected_check.strip()):
        if string not in verifier:
            raise SystemExit('Flow is corrected, but the verifier is not updated; review manually.')
    print('PASS: fix already applied; no changes needed.')
