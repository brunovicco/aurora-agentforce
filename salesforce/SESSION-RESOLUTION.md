# Authenticated Agentforce Session Resolution

## Scope

This laboratory investigates how authenticated Experience
Cloud customer identities can be correlated with native
Salesforce messaging sessions.

The experiments are diagnostic only. They do not authorize
business operations, expose customer records, or replace
independent policy enforcement.

## Experimental results

| Version | Access strategy | Observed result |
| --- | --- | --- |
| V2 | Current AuthSession | Unavailable in runtime |
| V3 | Apex execution identity | Customer identity observed |
| V4 | USER_MODE | QueryException observed |
| V5 | SYSTEM_MODE with sharing | NO_MATCH for both customers |
| V6 | Differential record sharing | Positive match after elevation for both customers |

### V6 differential experiment

The diagnostic action executes two identically scoped
queries within the same Apex transaction.

1. SYSTEM_MODE with sharing.
2. SYSTEM_MODE without sharing, only after NO_MATCH.

Both queries use the same actor identity, session
reference, channel restriction and session predicates.

| Actor | Baseline | Elevated |
| --- | --- | --- |
| Alice | NO_MATCH | CONSISTENT |
| Bob | NO_MATCH | CONSISTENT |

Both observations were supported by Apex runtime logs.

No exceptions, fatal errors or truncation were observed
in the two relevant V6 logs.

The result provides controlled evidence that record-level
sharing prevented session resolution in these scenarios.

It does not prove that the same behavior applies to every
Salesforce license, channel, deployment or agent runtime.

## Privilege boundary

The elevated query is encapsulated in a private inner
class declared without sharing.

The public entry point retains with sharing and derives
the execution identity from UserInfo.

The query requires:

- An exact messaging session reference.
- A matching authenticated end-user identity.
- The expected messaging channel.
- An active channel.
- An active messaging session.
- A non-null conversation reference.

Only a boolean diagnostic result is returned.

No business records are returned or modified by the probe.
The probe must not be treated as an authorization service.

## Experimental rollback

After collecting the V6 evidence:

- V5 was reactivated.
- V6 was confirmed inactive.
- The diagnostic elevated Apex grant was explicitly revoked.
- The pre-existing administrative grant was preserved.
- No unexpected explicit grants were observed.
- The diagnostic permission set contained no object or
  field permission rows.

The published V6 and its Apex classes remain available
as historical laboratory artifacts.

Do not activate V6 or enable its diagnostic grant as part
of a default deployment.

## Threat model

### Trust boundaries

The language model and user messages are not authoritative
sources of customer identity or authorization.

The platform execution identity, linked messaging context,
identity resolver and policy gateway represent distinct
trust boundaries.

### Threats and required controls

| Threat | Required control |
| --- | --- |
| Cross-customer session substitution | Bind session ownership to execution identity |
| Same-customer session replay | Verify current invocation binding and freshness |
| Guest or shared agent execution | Reject unexpected execution identities |
| Stale or ended messaging session | Validate session lifecycle |
| Logout or authentication expiry | Independently validate authentication validity |
| Revoked customer identity | Reject revoked or inactive identities |
| Prompt injection | Never derive trusted identity from model output |
| Excessive privileged access | Encapsulate fixed queries and minimize returned data |
| Resolver failure | Fail closed without privilege escalation |
| Sensitive diagnostic logging | Record outcomes without raw identifiers |

## Proposed Trusted Session Authorizer

The future authorizer must establish a trusted context
before verified business actions can execute.

Session ownership alone is insufficient. An active
MessagingSession is not proof of current authentication.

The authorizer must validate identity, invocation binding,
session freshness, lifecycle and revocation.

Business authorization must remain independently enforced
by the policy gateway.

Until these controls are implemented and validated, all
business actions remain outside the diagnostic channel.

## Reproduction artifacts

- V4: isolated/conversation-probe/
- V5: isolated/scoped-session-probe/
- V6: isolated/elevated-session-probe/
- Agent templates: isolated/identity-agent/templates/
- Restored permissions: isolated/identity-probe-access/

The packages are isolated from the primary force-app
deployment directory.

The V6 probe contains an intentional privilege elevation
for a controlled experiment. It is not production-ready.

## Evidence

- [V4 runtime evidence](../evals/identity-runtime-evidence-v4.json)
- [V5 runtime evidence](../evals/identity-runtime-evidence-v5.json)
- [V6 runtime evidence](../evals/identity-runtime-evidence-v6.json)
- [Future authorizer scenarios](../evals/trusted-session-authorizer-scenarios.json)

The published evidence omits raw logs, organization IDs,
user IDs, usernames, credentials and private trace state.

Apex unit tests include mocked dependencies. Passing these
tests does not establish adversarial runtime isolation.

## Remaining limitations

- Cross-customer adversarial runtime isolation is unverified.
- Current-invocation binding is unverified.
- Logout, expiration and revocation handling are unverified.
- Historical record visibility is not fully established.
- V4 Alice Apex evidence is not consolidated.
- Effective organization-wide permissions are not fully verified.
- Business authorization is not established.
- The definitive Trusted Session Authorizer is not implemented.
