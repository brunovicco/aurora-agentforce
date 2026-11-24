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
Salesforce identity provider or Apex action is implemented. Tests use fictional
in-memory bindings. Live org validation, durable revocation and channel-specific
identity assurance remain necessary. Existing Agent Script and Flow remain legacy.
