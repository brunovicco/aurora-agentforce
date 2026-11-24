# Verified integration contract — phase 2

The verified backend now exposes three operations in [openapi.verified.json](openapi.verified.json).
This is a candidate contract for trusted integration code, not an imported or deployed External Service.

| Operation | Result |
| --- | --- |
| getVerifiedOrder | Minimal order status |
| checkVerifiedReturnEligibility | Deterministic return policy decision |
| authorizeVerifiedCaseRequest | Ownership-checked order ID and customer-scoped request key |

All require the integration credential AND a signed customer session. The Case authorization
operation is read-only: it does not create, approve, or retrieve a Salesforce Case.
Its key is derived from the stored order owner, never from a chat argument. It deliberately
preserves the existing keys for both known synthetic customers. Other customer references use a
versioned SHA-256 digest of the exact customer/order/action tuple (no case folding), yielding
67 characters compatible with the Salesforce case-insensitive Text(100) fields. This is a
stable identifier, not a secret or approval token. The generated FastAPI schema and candidate
contract both declare the two credentials as an AND requirement.

## Salesforce cutover requirements

1. Authenticate the customer using a trusted channel/identity provider.
2. Resolve the current conversation to that authenticated identity server-side. A messaging ID
   or mutable Agent Script variable alone is not authentication.
3. Inject the short-lived signed session as a server-controlled HTTP header. Do not expose it
   as a reasoning action input, output, chat message or trace field. Named principal credentials
   alone cannot distinguish customers.
4. Replace the existing read action targets with trusted wrappers calling the verified API.
5. In the Case Flow, replace legacy order validation with authorizeVerifiedCaseRequest.
   Require HTTP 200, matching order ID and a nonempty returned request key; use that returned
   key for independent approval, existing Case lookup and unique Case creation.
   Never accept a request key from the agent. Keep native confirmation and approval-first ordering.
6. Remove the legacy opt-in from the deployed backend. Validate the wrappers and Flow in an
   isolated org before activation; verify agent permissions and trace redaction.

Phase 3 adds offline reference bindings and candidate internal Apex wrappers; see
[TRUSTED-CHANNEL.md](TRUSTED-CHANNEL.md). Actual authenticated channel binding,
metadata migration and live org validation remain pending. Do not import the contract directly as an agent action if doing
so exposes the customer-session credential to the model.

## Acceptance matrix for org validation (not run)

- Unauthenticated conversation: all three operations denied, no Case lookup.
- Customer A requesting customer B's order: same public response as a nonexistent order.
- Expired or revoked context: no protected operation.
- User-supplied identity, session ID or request key: cannot override trusted context.
- Valid owner without independent approval: no Case number or creation.
- Valid owner with current approval and confirmation: create/reuse one Case.
- Revoked approval with existing Case: no Case number.
- Two authenticated conversations: no identity leakage or cross-session token reuse.
- Confirm that logs and agent traces contain no signed session or signing secret.
