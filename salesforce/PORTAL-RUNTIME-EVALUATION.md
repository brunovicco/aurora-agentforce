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
