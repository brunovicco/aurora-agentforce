# Verified reads — development org acceptance runbook

Status: check-only Apex validation passed; authenticated channel acceptance remains NOT RUN.
Use synthetic accounts and orders only. The activation gate has not passed.

## 1. Check-only compilation and Apex mock tests

From the repository root, with the Salesforce CLI and a previously authenticated
development org alias:

```bash
bash scripts/sf-validate-verified-reads.sh aurora-dev
```

Confirm the target is a disposable Developer Edition or sandbox before running.
The script explicitly passes the alias and uses deploy start --dry-run, not an
actual deployment. It does not authenticate, print org credentials, activate an
agent or grant permissions. If the CLI returns a pending job ID, use
sf project deploy report --job-id <id> --target-org aurora-dev to inspect the
final result. Require successful terminal deployment validation, all specified
test classes executed and no failures. Record only sanitized aggregate results.
A successful check-only deployment is not evidence of authenticated agent runtime.

### Recorded evidence — 2026-11-24

Operator-reported Salesforce CLI output from the phase 4 branch at commit
`730e694fe9ccb8175a14a3527762591c69031c56` (branch head confirmed; local
commit inferred from the reported up-to-date checkout, not separately printed).

| Check | Result |
| --- | --- |
| Metadata API | 68.0 |
| Validation mode | dry-run |
| Terminal status | Succeeded |
| Components validated | 11/11 |
| Apex mock tests | 20 passed, 0 failed |
| Total elapsed | 6.69 seconds |
| Reported test time | 2110 ms |

Evidence source: sanitized operator-provided terminal output. Org username,
org ID and deployment ID intentionally omitted. No permanent deployment,
actual HTTP callouts, Named Credential injection, authenticated channel
execution or Agentforce action activation was demonstrated.
All 16 runtime acceptance scenarios remain NOT RUN.

## 2. Establish the actual trust boundary

Salesforce documents that an authenticated Experience site can associate a
messaging session with an active AuthSession; with Credential-Based User
Verification, a Service Agent can inherit the signed-in user's permissions.
These are platform capabilities, not observations about this org.

In a separate development-only experiment, verify the feature is available and
enabled on the actual channel, and determine a supported way to obtain the
current authenticated session and its conversation association within an action.
Do not infer this from ContactId, UserInfo.getUserId(), a linked variable or
a conversation ID alone. Do not expose raw AuthSession IDs, session tokens,
credentials or identifying records to the model or logs.

Use two fictional authenticated customers, A and B, with distinct orders
AUR-1001 and AUR-9001. Establish bindings through trusted infrastructure only.
The actual concrete SessionAuthorizer, broker scope policy, Named Credential
and runtime association must be validated before adding any invocable action.
If the channel cannot provide the required evidence, stop; do not fall back to
the fixed customer or an agent-selected identity.

## 3. Acceptance matrix — all rows initially NOT RUN

| ID | Scenario | Required evidence |
| --- | --- | --- |
| R01 | A authenticated, own order | Exact business result, correct order |
| R02 | B authenticated, own order | Exact business result, correct order |
| R03 | A requests B order | Generic unavailable, no B data |
| R04 | A requests nonexistent order | Same public result as R03 |
| R05 | Guest or unauthenticated channel | Denied before broker resolution |
| R06 | Conversation substitution | Denied before broker resolution |
| R07 | Logout or expired authentication | Next protected call denied |
| R08 | Broker binding revoked | Next protected call denied |
| R09 | Scope authorizer unavailable | Generic unavailable, no fallback |
| R10 | Malformed order identifier | No Orders API call |
| R11 | User attempts to set identity/token | Cannot override trusted binding |
| R12 | Read action permissions removed | Action denied |
| R13 | Broker credential missing | Generic unavailable |
| R14 | Both read operations | Correct minimal fields, no Case writes |
| R15 | Agent/debug/integration traces | No bearer tokens or signing keys |
| R16 | Legacy fixed-customer route | Disabled in verified deployment |

Record each ID, result (PASS/FAIL/NOT RUN), sanitized evidence reference,
tested commit and channel configuration. No credentials, personal data,
raw session identifiers or complete debug traces in repository evidence.

## 4. Cutover gate

All rows must pass in the actual target development channel before verified
read action activation. Mock and static CI results cannot replace this gate.
Case Flow migration requires a separate approval-first and idempotency review.
The existing Agent Script, External Service and Flow are unchanged.

Official references:
- https://help.salesforce.com/s/articleView?id=ai.service_agent_secure_actions_implement.htm&language=en_US&type=5
- https://developer.salesforce.com/blogs/2025/05/best-practices-for-building-agentforce-apex-actions
- https://developer.salesforce.com/docs/platform/salesforce-cli-reference/guide/cli_reference_project_deploy_start.html
- https://developer.salesforce.com/docs/platform/salesforce-cli-reference/guide/cli_reference_project_deploy_report.html
