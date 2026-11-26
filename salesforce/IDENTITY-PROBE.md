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

## Validation evidence

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

## Messaging infrastructure

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

## Remaining gates

- [ ] Permanent deployment explicitly approved.
- [ ] Credential-based user verification configured.
- [ ] Isolated diagnostic agent created.
- [ ] Trusted conversation context established.
- [ ] Alice authenticated identity verified.
- [ ] Bob authenticated identity verified.
- [ ] Guest access denied.
- [ ] Cross-customer substitution denied.
- [ ] Logout and expiry behavior verified.
- [ ] Missing session context evaluated.
- [ ] Shared agent execution identity evaluated.
- [ ] Wrong channel rejected.

No business actions may be exposed until the trusted
identity boundary is independently validated.
