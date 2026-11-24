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
