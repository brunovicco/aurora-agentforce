# Trusted channel adapter — phase 3 reference implementation

**Status:** offline Python reference and candidate internal Apex classes. No
authenticated Salesforce channel, production deployment, or Apex compilation
and execution in an org has been verified for this phase. Existing Agent Script
and Case Flow still use the isolated legacy fixed-customer integration.

## Trust boundaries

1. A trusted external channel authenticates the customer and authorizes the actual
   platform conversation. A conversation ID, ContactId, shared execution user or
   Named Credential alone is not proof of customer identity.
2. Trusted infrastructure registers the exact conversation, execution user,
   customer and expiration using internal Python methods. No HTTP enrollment,
   login or revocation endpoint is exposed.
3. An explicitly configured scope callback must authorize the current caller's
   conversation/user pair independently of the binding lookup. The reference
   callback interface is not a channel authentication implementation.
4. The private broker resolves the active binding and issues a signed short-lived
   bearer session. The trusted transport injects it into the Orders API header,
   never into agent reasoning inputs or outputs.
5. The Orders API checks both credentials, signature, expiry, active binding
   in broker mode, and ownership. Case creation still requires independent
   approval and native confirmation; ownership evidence is not write permission.

## Components

- Python trusted-channel resolver and allowlisted action transport: injected
  runtime context and per-call resolution; offline integration tests exercise
  the actual verified FastAPI routes.
- Optional ContextBroker (in memory) or SQLiteBindingStore (local durable state).
- AuroraVerifiedOrdersClient: fixed read-only callouts, typed strict responses,
  order and Case-key validation through the existing AuroraOrders Named Credential.
- AuroraTrustedContext and AuroraTrustedOrderActions: internal context boundary
  and order-only facade.
- AuroraBrokerBindingResolver: internal client using a separate candidate
  AuroraContextBroker Named Credential.

Apex classes are not invocable, REST-exposed or granted to the agent. The
trusted runtime wiring and Named Credential for the broker are not configured.

## Broker contract and configuration

Inject a BindingStore, separate broker_api_key and explicit broker_scope into
create_app. The broker is disabled by default; enabling it prohibits legacy
reads. The integration key, signing secret and broker key must be distinct.

POST /v1/context/resolve requires X-Aurora-Broker-Key and JSON conversation_id
and execution_user_id. A successful response includes conversation_id,
execution_user_id, expires_at (UTC), revoked=false and session_token.
Tokens expire within 300 seconds and no later than the binding expiry.
Replacement/revocation invalidates previous sessions at the Orders API.
The endpoint is intentionally excluded from the agent-facing OpenAPI contract.

Failures are generic: 401 credential, 404 binding/scope, 422 malformed request,
429 rate limit, 503 scope or storage failure. Handled responses use no-store.
The process-local global budget defaults to 120 well-formed requests per minute.
Malformed requests are sanitized but not counted by this budget. Use private
ingress, TLS, request-size limits and distributed admission controls for any
real deployment. Shared credentials do not independently constrain a caller
to its actual conversation: the scope callback must enforce that boundary.

## Persistence and audit

SQLite is optional; inject SQLiteBindingStore(Path(...)) instead of ContextBroker().
Use an operator-created private directory (0700 on POSIX), restrictive file
permissions and encryption where required. No bearer token or signing key is
persisted. Opaque identifiers and expiration are stored; state changes and
lifecycle events are transactional. The in-memory store loses state on restart
and must not be shared across workers. SQLite is not a distributed identity store.

SQLite records event types and timestamps, without customer/session identifiers.
HTTP outcomes are logged with fixed event names; enable INFO for issuance
events and use a protected sink. Neither trail is attributable or tamper-evident.
Retention, rotation, access control and external trace redaction remain pending.
Tokens are bearer credentials and can be replayed by a party possessing both
required credentials until expiry or revocation. Revocation does not cancel
already admitted requests. There is no proof-of-possession or key rotation.

## Isolated Salesforce validation (not run)

```bash
bash scripts/sf-validate-verified-reads.sh aurora-dev
```

Run from the repository root. See [the development org acceptance runbook](VERIFIED-READS-VALIDATION.md).

Verify supported API version and CLI options in the target org. Mock tests
cannot prove real Named Credential injection, customer authentication or
trace redaction. Before action/Flow migration, verify authenticated runtime
scope, two distinct conversations, no fallback to legacy access, expiration,
revocation, credential segregation, and logs/traces without secrets.
Use synthetic data only. See [verified cutover requirements](VERIFIED-INTEGRATION.md).

## Residual risks and next phase

A real channel (for example an authenticated Experience Cloud integration)
must establish identity and bind it to the current conversation. Do not infer
authentication from linked MessagingSession variables. No production scope
implementation, credential provisioning, org permission validation or
Agentforce/Flow migration is included. Do not activate the candidate classes
as agent actions before these prerequisites are verified.

