# Phase 4 — verified Agentforce actions

Candidate read facade only; not an activated agent action.

AuroraVerifiedReadFacade maps successful internal typed callouts to a minimal
business result and maps all unavailable paths to the same outcome with null
business fields. It exposes no token, customer reference, conversation identifier
or Case request key. It does not perform writes.

## Activation gate

Salesforce supports Apex actions and deterministic variable binding. A linked
MessagingSession identifier is a correlation value, not proof of customer identity.
Credential-Based User Verification in an authenticated Experience Cloud channel
can provide an authenticated execution context; validate this in the target org.
Do not treat a shared agent execution user as the customer.

Before adding InvocableMethod or modifying Agent Script:
- Prove the authenticated runtime and exact conversation binding independently.
- Provision the separate broker Named Credential and a restrictive scope policy.
- Verify caller permissions, channel isolation and no token exposure in traces.
- Compile the candidate classes and execute their mock tests in a development org.
- Confirm missing, expired, revoked or cross-customer context returns unavailable.
- Confirm malformed input cannot reach callouts and no legacy fallback exists.

The current legacy Agent Script, External Service and Case Flow remain unchanged.
The verified read facade is internal and has no agent permission grant. Case
migration follows only after read isolation is verified.

References:
- https://developer.salesforce.com/docs/ai/agentforce/guide/ascript-ref-actions.html
- https://developer.salesforce.com/sample-apps/agent-script-recipes/action-configuration/advanced-input-bindings
- https://developer.salesforce.com/blogs/2025/05/best-practices-for-building-agentforce-apex-actions

Run the isolated manifest validation described in TRUSTED-CHANNEL.md, adding
AuroraVerifiedReadFacadeTest to the specified test classes. No org validation
has been performed for this candidate.

## Authenticated runtime composition

AuroraAuthenticatedReadRuntime requires an independent SessionAuthorizer and
a BindingResolver. It checks the actual runtime execution user and trusted
conversation correlation before constructing the read facade on every operation.
A missing authorizer, negative or null decision, or exception denies access
without resolving a broker binding. No permissive default is supplied.

The SessionAuthorizer is an interface, not a Salesforce authentication
implementation. The caller must obtain the conversation correlation from
platform-controlled context and verify a live authenticated session. Do not
expose the runtime method directly as an invocable action or accept its
conversation argument from the model. The broker scope policy remains an
independent downstream boundary.

Salesforce documents authenticated Experience Cloud messaging AuthSessions
and private action scoping in:
https://help.salesforce.com/s/articleView?id=ai.service_agent_secure_actions_implement.htm&language=en_US&type=5
Salesforce explicitly advises against treating context variables as authentication:
https://help.salesforce.com/s/articleView?id=ai.service_agent_context_variables.htm&language=en_US&type=5

In the development org, confirm whether the authenticated session can be
resolved reliably in the actual action execution context; verify two distinct
authenticated users, guest denial, logout/expiry, and conversation substitution.
Capture evidence without logging credentials. Add AuroraAuthenticatedReadRuntimeTest
to the isolated manifest validation test list. These mock tests are authored,
not executed in an org. No concrete AuthSession lookup, permission grants,
or invocable actions are included.
