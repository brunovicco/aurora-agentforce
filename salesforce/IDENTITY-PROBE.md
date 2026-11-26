# Aurora Authenticated Identity Probe

## Purpose

Validate the execution identity and session context
of an isolated Agentforce Service Agent.

This diagnostic is not an authorization boundary.

## Infrastructure

The following metadata packages are maintained separately
from the default Salesforce deployment:

- identity-probe
- messaging-setup
- messaging-routing
- messaging-channel

Administrative permission assignment is an explicit
operator-controlled operation.

The Embedded Service Deployment and its generated site
are environment-specific and are not included.

## Initial validation evidence (historical)

Metadata API version: 68.0.

Identity Probe revision 3:

- Components validated: 2/2.
- Apex tests passed: 9/9.
- Apex test failures: 0.
- Validation mode: dry-run.
- Permanent deployment: not performed.
- Runtime identity verification: not performed.

Previous revisions exposed two issues:

- Native session retrieval is unavailable in Apex tests.
- Custom Apex exception names must end in Exception.

Session retrieval was isolated behind an injectable
provider to enable deterministic unit testing.

## Initial messaging infrastructure (historical)

- Authenticated Messaging Channel provisioned.
- Channel inactive at last verification.
- Dedicated routing configuration and empty queue.
- Embedded Service Deployment created.
- Guest users disabled in deployment metadata.
- Separate guest identity for the generated ESW site.

The ESW permission inventory is not proof of effective
permissions or runtime isolation.

## Security boundaries

The probe:

- Does not perform DML.
- Does not perform external callouts.
- Does not access business records.
- Does not return session tokens or user identifiers.
- Does not authorize business actions.
- Does not establish conversation ownership.

Native session retrieval can still fail in runtime.
Mocked Apex tests do not establish platform behavior.

## Runtime experiment — 2026-11-26

Credential-based user verification was configured in the
Messaging Channel and Experience Builder.

The authenticated channel was activated and the isolated
RoutingFlow was associated with the diagnostic agent.

### Agent V2 baseline

- Original Apex probe deployed: 9/9 tests passed.
- Authenticated chat and diagnostic routing observed.
- Two MessagingSessions associated with Alice.
- Apex probe execution observed in a log attributed to Alice.
- Native session retrieval failed with System.UnexpectedException:
  Current session unavailable.
- Direct UserInfo evidence and unique conversation binding
  remain unverified.

This demonstrates why execution identity and native session
availability must be treated as separate controls.

### Agent V3 remediation

- Execution Identity Probe deployed: 8/8 tests passed.
- No dependency on Auth.SessionManagement.
- Runtime identity obtained from platform UserInfo.
- Only boolean diagnostic outputs and log markers.
- Both diagnostic classes granted to Alice and Bob through
  the dedicated permission set.
- No object or field permission rows in that permission set.
- V3 validated and published, but inactive.
- V2 remains active.

### Reproducibility

Additional isolated packages:

- execution-probe
- identity-probe-access
- messaging-channel-flow-routing
- identity-inbound/templates
- identity-agent/templates

The initial messaging-channel package is a historical
baseline. Do not deploy both channel revisions together.

Agent and Flow templates contain environment placeholders.
Render them privately and validate before deployment.
Never commit resolved usernames, org IDs, session tokens,
raw logs or environment-specific backups.

See:

- evals/identity-runtime-scenarios.json
- evals/identity-runtime-evidence-v2.json

## Remaining gates

- [ ] Activate V3 with explicit operator approval.
- [ ] Establish fresh diagnostic conversations.
- [ ] Verify Alice and Bob execution identity.
- [ ] Establish unique trusted conversation binding.
- [ ] Verify guest denial and identity substitution resistance.
- [ ] Verify logout, expiration and missing context.
- [ ] Reject shared agent identity and wrong channels.
- [ ] Validate deterministic authorization before exposing
      any business action.

The probe is diagnostic, not an authorization boundary.
No business actions may be exposed until the trusted
identity boundary is independently validated.
