# Salesforce — Aurora demo setup and verified status

**Partial milestone (November 21, 2026).** The integration was configured and exercised in a Salesforce Developer Edition with real Agentforce actions and Salesforce `Case` records. This guide separates verified behavior from org-specific setup and unfinished work. **It is not an automatic installer or a production-ready customer support solution.**

[Main README (English)](../README.md) · [Brazilian Portuguese overview](../readme.pt-BR.md)

## Implemented components

- Agent Script bundle: `force-app/main/default/aiAuthoringBundles/Aurora_Pos_Venda_1/` with `Get_Order`, `Check_Return_Eligibility`, and `Create_Support_Case` actions.
- External Service `AuroraOrdersService`, exposing `getOrder` and `checkReturnEligibility`, backed by the `AuroraOrders` Named Credential.
- Autolaunched Flow `AbrirCasoPosVenda` with input `order_id` and outputs `case_number` and `outcome`.
- Unique `Case.AuroraRequestKey__c` field for idempotency.
- `AuroraCaseApproval__c` custom object with `RequestKey__c`, `Approved__c`, and `ExpiresAt__c` for independent approval.
- Permission Sets `Aurora_API_Access`, `Aurora_Approval_Read`, and `Aurora_Case_Access`.

Source and metadata are committed. External Credential secrets, local Salesforce CLI sessions, org records, and the temporary tunnel URL are **not** committed.

## New backend security increment (not deployed to the org)

The backend provides `/verified/orders/{order_id}` and `/verified/orders/{order_id}/return-eligibility`, each enforcing an integration key **and** a signed short-lived customer session. Identity comes from a trusted issuer, never from the chat or an LLM-selected action parameter. Offline tests cover isolation, expiry, revocation injection and tampering. No public token issuer is exposed; an optional private broker is described below.

**The currently deployed Agentforce External Service, Agent Script and Case Flow still use the legacy fixed-customer routes.** They have not been migrated to the verified paths, and no Salesforce org tests have been run for this increment. For the original isolated demo to work with this version of the backend, explicitly set `AURORA_ENABLE_UNVERIFIED_DEMO_READS=1`; do not enable this in a public customer channel. Without that opt-in, legacy routes return 403. Verified routes need `AURORA_CUSTOMER_SESSION_SECRET` and return 503 without it. Keep the signing key outside Salesforce prompts, metadata and agent arguments.

Next steps for a **real** Salesforce integration: authenticate the consumer via a trusted provider/channel, propagate a short-lived context through a server-controlled integration (not chat or LLM parameters), validate it for **both** read operations and the Flow, scope Case approval/idempotency keys to the verified customer, configure durable revocation and document org validation evidence. The original Flow remains unchanged to avoid pretending these controls are already wired.

## Phase 2 candidate contract

The verified backend now derives the customer-scoped Case request key from the authorized order. See [verified integration and cutover requirements](VERIFIED-INTEGRATION.md). The current Salesforce actions and Flow have not been migrated or deployed for phase 2.

## Connect the Orders API

The local Python service requires an `AURORA_API_KEY` of at least 32 characters and validates the `X-API-Key` header. Use the tested [OpenAPI 3.0.3 contract](openapi.json) for the Salesforce External Service.

Start the API as described in the [main README](../README.md). For a temporary public HTTPS URL during development, run:

```bash
cloudflared tunnel --url http://localhost:8000
```

The Cloudflare Quick Tunnel changes its URL and requires the local API to remain running. It was used for integration tests, **not** as permanent hosting.

The org-specific setup includes:

1. Create External Credential `AuroraApiAuth` with named principal `AuroraDemoPrincipal` and a protected API key parameter.
2. Set the `X-API-Key` header using that protected credential parameter; do not embed the key in source or metadata.
3. Configure Named Credential `AuroraOrders` with the current HTTPS endpoint and grant its principal access to the agent execution user through `Aurora_API_Access`.
4. Register `AuroraOrdersService` against that Named Credential. For a new org, verify dependency order, permissions, and API compatibility.

**The key authenticates the Salesforce-to-API integration, not the customer in the conversation.** The current Agentforce connection still uses fixed `customer-demo-001`. The new verified API routes are not integrated with the org and do not independently authenticate people.

## Authorization and idempotency in the Flow

The Flow revalidates the order through the API and builds a deterministic key such as `customer-demo-001:AUR-1003:post-sale` (all synthetic data).

Verified execution order:

1. Require HTTP `200`, a non-null returned `order_id`, and an exact match with the requested ID.
2. Find an independent approval with matching `RequestKey__c`, `Approved__c = true`, and a future `ExpiresAt__c`.
3. **Only after approval**, look for an existing Case or create one using the unique request key.
4. Return `created` or `existing` with a genuine `case_number`; `approval_required`, `unavailable`, and `failed` do not disclose a Case number.

The `Create_Support_Case` action requires native Agentforce confirmation. A conversational `yes` does **not** replace independent approval. Authorization is a custom record managed separately by an authorized user; this demo does **not** include a native Salesforce Approval Process or automated customer consent. Never grant the agent create/edit/delete rights on approval records.

## Validate with a Developer Edition org

From `salesforce/`, after authenticating your org (example alias: `aurora-dev`):

```bash
sf agent validate authoring-bundle \
  --api-name Aurora_Pos_Venda_1 \
  --target-org aurora-dev \
  --api-version 68.0

python3 ../scripts/verify_aurora_flow.py

sf agent preview start \
  --authoring-bundle Aurora_Pos_Venda_1 \
  --use-live-actions \
  --target-org aurora-dev
```

The bundle validation completed with **zero errors**, and the corrected Flow was deployed and active in the tested org. After starting a preview, use the returned session ID:

```bash
SESSION_ID="PASTE_RETURNED_SESSION_ID"

sf agent preview send \
  --authoring-bundle Aurora_Pos_Venda_1 \
  --session-id "$SESSION_ID" \
  --utterance "Please open a support case for order AUR-1003." \
  --target-org aurora-dev

sf agent preview send \
  --authoring-bundle Aurora_Pos_Venda_1 \
  --session-id "$SESSION_ID" \
  --utterance "yes" \
  --target-org aurora-dev

sf agent trace read \
  --session-id "$SESSION_ID" \
  --format detail \
  --dimension actions
```

**Warning:** `--use-live-actions` can write actual Salesforce records. Avoid repeating approval updates or create requests without understanding the current org state.

### Evidence collected in the org

- `AUR-1003`: a real Case was created, then returned as the existing Case when approval was valid, without duplication.
- Revoked approval: `approval_required` was returned **without disclosing an existing Case number**. Raw trace showed `case_number = ''`.
- Negative confirmation: the Case action was not invoked in the tested preview.
- User-facing wording was corrected to request support-team authorization instead of claiming a formal Salesforce approval channel.
- `ObjectPermissions`, `FieldPermissions`, `PermissionSetGroupComponent`, and `UserRecordAccess` were inspected for the Einstein Agent user. Approval records were readable, not creatable/editable/deletable; Cases were readable/creatable, not editable/deletable, under the inspected permissions.

These are **targeted manual tests**, not a complete Testing Center report or a production security guarantee.

## Demonstrated customer-identity gap

A live preview of `What is the current status of order AUR-1003?` returned its product and `shipped` status **without verifying the end customer's identity**.

This separates integration authentication from customer authentication. The approval guard covers Case lookup/creation; order status and return eligibility still rely on a fixed synthetic customer. The `VerifiedCustomerId` variable in Agent Script is only reserved for future use; **it is not proof of authentication**.

**Do not expose the agent as a public customer-support channel until customer-level authorization is enforced by both the backend and the Flow.**

## Remaining work

1. Introduce a trusted customer authentication/session mechanism (OTP is a design option, **not implemented**).
2. Propagate tamper-resistant authenticated context; validate customer-to-order ownership for both External Service reads and the Case Flow; bind approvals and Cases to verified identity.
3. Fail closed without verified identity; cover cross-customer reads, session expiration, and revocation in tests.
4. Validate a complete fresh-org deployment, dependencies, and secure credential setup. The DX scripts and metadata workflow are versioned but are not evidence of fully automated provisioning.
5. Execute and report all [12 Agentforce evaluation scenarios](../evals/scenarios.json), including negative tests, action traces, and latencies; record a reproducible demo.

This project uses **fictional data** and does not perform real refunds.

## Trusted channel reference boundary

See [TRUSTED-CHANNEL.md](TRUSTED-CHANNEL.md) for the optional broker, explicit
scope policy, SQLite storage, local rate limiting and isolated Apex validation
manifest. Broker mode requires a separate credential and disables legacy reads.
The candidate AuroraContextBroker Named Credential is unconfigured. No agent
class access, production identity integration or action/Flow migration is
included. Do not expose the broker or activate candidate actions before
validating the authenticated runtime binding in an isolated org.

See [VERIFIED-ACTIONS.md](VERIFIED-ACTIONS.md) for the candidate read facade and activation gate. Add AuroraVerifiedReadFacadeTest to isolated Apex validation; do not activate the facade before authenticated runtime verification.

Include AuroraAuthenticatedReadRuntimeTest in isolated validation. Its injected session authorizer is not an implementation of Salesforce AuthSession verification.
