# Portal runtime evaluation

This plan is for an isolated non-production deployment of the candidate portal with synthetic users only. Do not attach the legacy agent. Do not deploy over the published site until an explicit backup, change and rollback plan is approved.

## Evidence protocol

Use [the scenario plan](../evals/portal-runtime-scenarios.json) and copy [the blank evidence template](../evals/portal-runtime-evidence.example.json) to a private directory. Set candidate_commit to the full hash of the deployed candidate. Each observation must come from an actual session (guest, Alice or Bob), not an admin-side query or a mock. Use separate browser profiles for the two customers and a fresh guest session. Keep raw screenshots and identifiers outside Git. Use EV-001 style references to locally retained, redacted evidence. The data_disclosed flag means unauthorized disclosure, not intended own-account data. The mutations field counts unintended business record changes, not normal authentication/session records. For direct Case or Flow attempts, verify the absence of new business records or side effects with an administrator in the isolated environment. Stop testing on unexpected disclosure or mutation.

Expected own-account read is conditional on the approved portal policy and intended fields. If the route is unavailable, do not mark the scenario passed; document the deviation. For denied outcomes, login redirect or explicit denial with no unauthorized data and no business writes is acceptable. A hidden navigation shortcut alone is not evidence of denial: test the direct route where applicable.

Run from repository root:

```bash
uv run python scripts/portal_runtime_eval.py /private/path/evidence.json
```

The evaluator scores reported evidence deterministically, not independently. Missing observations remain not_run. A full set of reported passes never authorizes activation.

## Before candidate deployment or publication

- Establish whether a separate development org/site is available; if not, stop and explicitly review the existing published site's backup and rollback plan.
- Record exact candidate revision, rendered metadata inventory and dry-run result.
- Review effective profile/permission sets, group muting, CRUD/FLS, external sharing, direct routes and guest configuration.
- Confirm the legacy Agentforce channel is disconnected.
- Review the actual Experience Builder preview and test with synthetic accounts only.

## Before Agentforce integration

Require real session isolation evidence, trusted current-conversation identity, explicit authorization of action execution, separate broker credentials, verified read action tests and independent Case approval controls. The verified-actions candidate in PR #5 remains separate; no connection is authorized by the portal evaluator.

## First published-site observations (2026-11-25)

Publication succeeded in the dedicated development org after operator approval. Alice independently logged in successfully after publication, according to operator report; screenshot shows the published Aurora home. Verify the displayed profile identity before marking P02 passed. Bob and a fresh anonymous session must be tested separately after publication. Earlier guest login challenge and administrator-side record access are preliminary evidence, not substitutes for post-publication direct-route tests. Do not enable any messaging channel. Stop on unexpected business-data disclosure or mutation.

## Published profile observations and next read-only checks

Operator screenshots show separate named Alice and Bob profiles and a login screen. P02/P03 identity observations are supported by the screenshots; independence of browser sessions and absence of unintended writes must still be confirmed in the private evidence ledger. Login screen alone does not establish denial on a protected business route. Both profiles expose Edit, Feed, Cases, Groups, Files/upload, Followers/Following and Influence; these are UI affordances, not established grants. Do not post, upload, edit or create records during initial review. The versioned routes expose `profile`, `comm-my-account`, `account-management`, `case`, `contactsupport` and `flow` prefixes. First use actual profile URLs obtained from each synthetic session (not guessed IDs) to test cross-profile read isolation, then test `comm-my-account` and `account-management` read-only. A blank, generic error or missing route is inconclusive unless authorization denial can be established. Guest must attempt a protected business route, not merely the login page. Stop on unintended data disclosure. Do not share full profile URLs, identifiers or email addresses in public artifacts. Evaluate account record access separately from self profile access. No Agentforce connection or permissions change authorized.

## Reported cross-profile checks

Operator reported denial for Alice accessing Bob's profile, Bob accessing Alice's profile and anonymous access to Alice's profile. These are three manual profile-route observations, not independent verification of all User records or Account authorization. The `comm-my-account` view binds headline and record tabs to `CurrentUser.accountId`; `account-management` binds member list and branding to the same identity-derived account. Review both in each synthetic session without edits. Neither route alone tests arbitrary Account record identifiers. Record own-account display and visible write affordances; do not infer FLS or deny-write from UI. Guest must also attempt the business account route. Stop on cross-account data disclosure. All CI workflows for `1564907` succeeded.

## Account route observations — guest verification blocked

Operator reported own-account-only data for both customers on `comm-my-account` and `account-management`. The guest check on `comm-my-account` was also reported as own data, an ambiguous and unexpected result for an unauthenticated principal. Treat P01 as unresolved and block further integration until a clean independent browser session confirms the actual identity and route behavior. If customer data is displayed without authentication, stop and contain exposure; do not expand grants. No claim of cross-account record isolation or read-only enforcement follows from these observations. Do not record P04/P05 as passed solely from own-account display. No org mutation performed by this documentation update.

## Guest retest and direct Account record checks

Operator retested `comm-my-account` in an independent guest session and reported redirect to login. The earlier ambiguous guest result was not reproduced; its cause is unknown. Direct `detail/<AccountId>` checks showed own Account A/B respectively for Alice/Bob, denial/login for both cross-account attempts, and denial/login for guest on Account A. Guest on Account B was not run. This supports read isolation in the tested routes only; read-only enforcement, FLS, other records and logout remain pending. All three CI workflows for `b11dde7` succeeded.

## Next gate: Case creation surface

The versioned `contactsupport` view contains `forceCommunity:contactSupportForm` configured with `NewCommunityCase`, `GuestCommunityCase` and attachments enabled. The generic `createrecord` view binds `actionApiName` to a route attribute. These are potential direct write paths; existence is not proof of effective authorization. Inspect `contactsupport` and `case` in isolated customer and guest sessions first, without submitting or uploading anything. A rendered form or empty list does not establish creation permission or denial. Record whether the form, existing records, or explicit denial are displayed; stop if unauthorized records appear. Before any synthetic write attempt, review effective grants and establish a narrowly scoped before/after record audit and separate operator approval. Do not activate flows or connect agents.

## Case surface observation

Operator reported Case list unavailable/error for Alice and Bob, Contact Support form visible to both, and denial/login for guest on both routes. No form submission was requested or reported. P08/P09 remain unverified; errors on Case lists are inconclusive. Repeat the existing read-only grants inventory after publication and inspect effective Case object access in the administrator UI before authorizing any synthetic write attempt. A later UI hardening change should remove the unnecessary support form and generic write surfaces, but must not be treated as backend authorization. Keep the existing deployed metadata candidate unchanged until a separate change plan and fresh backup are approved. All three CI workflows for `b653bd2` succeeded.

## Post-publication grants audit

Operator reran `sf-audit-portal-grants.sh aurora-dev` after fast-forward to `ce44849`. Report: no observed disallowed grants, no field grant objects, no broad system grants, no additional review gaps, three source_inventory_incomplete gaps (both customers and guest), review_required, effective_permissions_verified=false, runtime_access_verified=false, mutations=0. This matches earlier observations; source completeness is deliberately false in the normalizer. Own-account runtime reads demonstrate why empty grant findings cannot be interpreted as zero effective permissions. Review actual Case object access and assignment sources for both customers using administrative user access summaries, and site guest profile separately. No form submission, grant change or agent activation authorized. P08/P09 remain pending.

## Read-only preparation for a controlled Case probe

A narrow marker audit is available: `bash scripts/sf-audit-portal-case-probe.sh aurora-dev AURORA-PROBE-0123456789ABCDEF`. Use a fresh random marker per actor, consisting of 16 uppercase hexadecimal characters after the fixed prefix. Run the audit before any approved probe; require zero matching Cases. This script only queries exact Subject equality and prints a count; it does not submit, delete or modify records. It is not an org-wide side-effect audit: automation could change the subject, create other records or run asynchronously. A zero count alone cannot establish denial. Before any actual submission, inspect effective Case permissions and associated automation, freeze concurrent changes, obtain separate operator approval, and capture a broader before/after audit appropriate to the automation. Stop if a Case is created or the outcome is unclear; do not retry or delete automatically. No actual write attempt is authorized yet.

## Case probe baseline evidence

Operator ran the marker audit for two distinct random synthetic subjects on revision `d5eb786`. Both returned matching_case_count=0, exact_subject_only, runtime_access_verified=false and mutations=0. All three CI workflows passed. Marker values are retained locally, not committed. No submission authorized. Before any probe, inspect Case in Flow Trigger Explorer (create/update, including asynchronous paths), active Case Apex triggers, Case assignment/auto-response/escalation rules, and effective Case permissions for both customers. Do not activate, disable or edit automation during review. Recheck the marker baseline immediately before any separately approved submission. An exact-subject count cannot establish absence of other side effects.

## Case automation inventory observations

Operator Tooling API queries returned zero ApexTrigger rows for TableEnumOrId Case and exactly one FlowDefinition with non-null ActiveVersionId, AbrirCasoPosVenda. The versioned Flow is an autolaunched flow, but the active org version has not been compared to the source. These queries do not exhaust managed automation, assignment, auto-response, escalation or other side effects. Effective customer Case permissions and administrative automation review remain pending. No write attempt authorized. CI status of the preceding revision was reviewed separately.

## Administrative Case and customer access observations

Operator screenshots show active Standard Case assignment rule with five entries based on account country, SLA and type, all assigned to the same internal owner and with email boxes unchecked. The setting to apply assignment rules to community portal Cases is unchecked. No Case auto-response rules are configured. Standard escalation rule is active; its entries and actions have not been inspected. Object Manager Case Flow Triggers lists zero items, corroborating the earlier Tooling API inventory. Alice is active with Customer Community license and Aurora Customer profile; the user detail page shows zero ordinary, activation-required, group and permission-set-license assignments. The View Summary button is available but its object-permission contents have not been supplied. Bob's assignment details and effective Case permissions remain unverified. No raw screenshots, addresses, login IPs or identifiers retained in Git. Do not submit a Case until escalation actions, effective permissions and side-effect audit have been reviewed and the operator separately authorizes the probe. No Salesforce mutation performed.

## Blocking object-permission discrepancy — 2026-11-25

Alice's administrative User Access Summary shows Case read/create/edit and Order read/create/edit/delete, contrary to the target policy. Account and Contact show read only. Additional business objects have write grants, including Contract, ReturnOrder, Asset, WorkOrder and Shipment. This is positive administrative grant evidence, not proof of successful record mutation or credential exposure. The prior SOQL inventory missed these grants despite reporting incomplete sources; its empty findings must not override this evidence. Root cause of the discrepancy remains unverified. Bob and guest effective grants remain pending. The Standard escalation rule has eight criteria entries based on account billing country, SLA and Case priority; actions have not been inspected. Cancel the planned write probe until least-privilege remediation is reviewed. Identify sources via row-level Access Granted By, inventory all users of the custom profile, back up current profile and review dependencies before any approved change. Do not modify the agent execution profile or activate the agent. All three CI workflows for `9c84004` passed.

## Confirmed grant source and remediation gate

Alice's Access Granted By screenshots show Aurora Customer as the sole granting profile for Case (read/create/edit) and Order (read/create/edit/delete); zero permission sets and groups for both objects. This confirms the grant source, not the cause of the SOQL inventory discrepancy. All three workflows for `4c534e0` passed. Before changing the profile, inventory all assigned users (including inactive users), preserve private profile metadata with explicit relevant CustomObject members, inspect captured permission rows against the administrative summary, and validate a scoped restoration dry-run. Profile retrieval is component-dependent and must not be described as a full backup. See https://developer.salesforce.com/docs/platform/api-metadata/references/meta-types/metadata-profile.html. Keep retrieved object definitions out of any profile-only deployment. No permission change, Case submission or agent activation authorized.
