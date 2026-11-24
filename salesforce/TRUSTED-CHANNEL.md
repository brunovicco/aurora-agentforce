# Trusted channel adapter — reference boundary

This increment adds a Python reference resolver, not a deployed Salesforce adapter.
The trusted channel must first authenticate a customer and establish a binding between
the platform conversation, exact customer reference and signed session identifier.
The resolver verifies that binding, including expiry and revocation, on every resolution.

The conversation identifier supplied to this resolver MUST come from trusted runtime
context. It is not a bearer credential. Never expose a public lookup endpoint taking
only a conversation ID, or accept a conversation ID supplied by an LLM or chat text.

## Integration sequence

1. Channel authenticates the customer outside the agent.
2. Trusted infrastructure establishes and stores the binding. The lookup is scoped
   to the current authorized platform conversation, not to user-selected identifiers.
3. Resolve the binding and validate signed customer claims before any action.
4. Trusted transport injects the signed session in the verified API header.
5. The API checks integration credentials, session and order ownership.
6. Case creation still requires native confirmation and independent approval.

The identity-only Python resolver returns only the verified customer identity. The internal
binding resolver is used by a trusted transport facade, which injects credentials into an
allowlisted verified route after checking the current binding on every call. The facade is
constructed by trusted runtime code and accepts only an operation and order ID at execution.
Offline integration tests exercise the actual FastAPI endpoints through an injected transport;
no public lookup or token relay endpoint is introduced.
A future Salesforce wrapper must independently obtain the current trusted context,
inject the credential without exposing it to the reasoning model or traces, and
deny requests if any binding is absent or invalid.

The resolver is dependency-injected. No production HTTP client, persistence, public issuance endpoint, native
Salesforce identity provider or invocable Apex action is implemented. Tests use fictional
in-memory bindings. Live org validation, durable revocation and channel-specific
identity assurance remain necessary. Existing Agent Script and Flow remain legacy.

## Internal Apex callout client (candidate, not compiled in an org)

`AuroraVerifiedOrdersClient` implements three typed read-only callouts through
`callout:AuroraOrders`. The existing Named Credential must supply the integration
API key. The trusted caller supplies the signed session; the client does not
authenticate a conversation or mint tokens. It accepts fixed operations, validates
order IDs and token syntax, rejects non-200 and malformed or mismatched results,
and returns generic errors without including response bodies or credentials.

The class deliberately has no InvocableMethod, AuraEnabled, REST resource or agent
action exposure. Do not add any of those until trusted context resolution is wired.
Do not grant new Apex class access to the agent as part of this increment.

Use the isolated manifest only in a configured development org:

```bash
cd salesforce
sf project deploy validate --manifest manifest/aurora-verified-client.xml \
  --target-org aurora-dev --test-level RunSpecifiedTests \
  --tests AuroraVerifiedOrdersClientTest --tests AuroraTrustedContextTest \
  --tests AuroraBrokerBindingResolverTest
```

Check the org's supported API version and CLI options before running. The Apex
mock tests are authored but not executed here. They cannot verify actual Named
Credential injection, platform authentication or debug-log redaction. Validate
those separately before exposing any action. Never deploy against real customer data.

## Internal Salesforce context boundary

The candidate Apex facade AuroraTrustedOrderActions accepts only an order ID per
business method. AuroraTrustedContext requires an injected BindingResolver and
a trusted conversation identifier at construction. It checks the exact conversation,
current execution user, expiry, revocation and token syntax on every call. The
backend remains responsible for signature validation and ownership. The execution
user is NOT evidence of customer identity, particularly for shared service-agent users.

No concrete production resolver is installed. An authenticated Experience Cloud
channel with Credential-Based User Verification is one candidate to investigate;
linked MessagingSession variables are system-populated identifiers, not proof of
authentication. A trusted issuer must independently establish the binding and ensure
that it is current for the actual conversation. Do not bind the constructor to
arbitrary action input or grant the agent access to tokens or resolver configuration.
The classes are internal, not invocable, and the isolated manifest is unchanged
in deployment scope (candidate classes only). The new mock tests are not compiled
or executed in a Salesforce org.

References:
- https://developer.salesforce.com/docs/ai/agentforce/guide/ascript-ref-variables.html
- https://developer.salesforce.com/blogs/2025/05/best-practices-for-building-agentforce-apex-actions

## Concrete broker client (candidate)

AuroraBrokerBindingResolver calls a separate Named Credential, AuroraContextBroker,
using POST /v1/context/resolve. It checks exact conversation and execution-user
correspondence, expiry, revocation and token syntax. It rejects non-200 and malformed
responses without returning their diagnostic details. No bearer token is stored in
Salesforce custom fields. The existing AuroraOrders credential is not reused.

The external broker must authenticate the calling infrastructure and independently
authorize the current conversation. The request identifiers are correlation values,
not proof of authentication; a shared Salesforce user or integration credential
alone is insufficient. The broker must derive its answer from an authenticated
channel binding, not mint a session merely because these identifiers were supplied.
No actual broker endpoint, Named Credential configuration, durable storage, identity
provider, permission grant or runtime context wiring is included here. This client
must remain internal until those controls are implemented and validated.

Expected broker contract: POST JSON conversation_id and execution_user_id;
200 JSON conversation_id, execution_user_id, expires_at (UTC date-time),
revoked (boolean), session_token (signed Aurora session). Deny unavailable,
unauthorized, expired or revoked bindings with non-200. Never log session_token.
The backend independently validates the token. Mock tests do not establish
Salesforce credential injection, authentication or trace redaction.

Reference: https://developer.salesforce.com/docs/platform/apex-dev/references/apex-dev/apex-callouts-named-credentials.html

## Python broker reference service

The existing FastAPI app can optionally receive an internal ContextBroker instance
and a separate broker_api_key. Registration and revocation are Python-only methods
for trusted infrastructure; there is no public enrollment or login route. The
candidate Apex Named Credential must inject X-Aurora-Broker-Key. The broker
resolve endpoint is absent unless explicitly configured, returns short-lived
signed tokens only for registered exact conversation/user pairs, and uses
Cache-Control: no-store on successful replies. Broker mode disables legacy reads
and requires every verified API session to remain active in the same store.
Replacing or revoking a binding invalidates previously issued tokens.

This is a process-local reference store, not durable persistence. Tokens are not
stored. Do not use multiple workers or enable the endpoint in a public channel.
A shared broker credential authorizes trusted infrastructure, not a human or
a conversation: the caller must independently enforce current conversation
scope. A compromised broker caller could request other registered pairs.
No actual channel authentication, durable audit store, external storage or
Salesforce credential configuration is implemented. The previous description
of an absent broker endpoint refers to the earlier Apex-only increment.
