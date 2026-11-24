# Customer access boundary — audit protocol

The [target policy](portal-access-policy.json) is deliberately restrictive and **not verified** against the org. No profile or permission-set changes are deployed. The existing synthetic Alice and Bob accounts are distinct; confirm this again in the org. Never publish usernames, record IDs, session identifiers or credentials.

## Read-only configuration review

In Setup, review the Aurora Customer profile and both test users' assigned permission sets and permission set groups (including muting). Review the site guest user separately. Record effective grants, not just profile defaults. Inspect object CRUD, View All/Modify All, field visibility and editability, Apex class access, Flow access and system permissions. Review external sharing defaults, sharing rules, sharing sets, account relationships and manual shares. Review the actual site navigation and direct record routes. A missing grant in one profile is not proof of denial.

| Target | Required result for initial portal |
| --- | --- |
| Account, Contact, User | Read own record only if required; minimal fields; no direct mutation |
| Case, AuroraCaseApproval__c, Order | No direct CRUD or broad object permissions |
| MessagingSession, MessagingEndUser | No direct CRUD or broad object permissions |
| Integration Apex, arbitrary business Flow | No direct customer execution |
| Guest | No business record or operation access |

Do not remove Salesforce-required identity or login capabilities blindly. Record deviations and assess their effects before changing grants. Customer Community licensing and platform-imposed permissions may constrain the target; treat deviations as review blockers rather than silently accepting them.

## Runtime evidence matrix

Use two separate private browser sessions for the synthetic external users and a third unauthenticated session. Use only fictitious records and a dedicated non-production environment. Do not deploy the candidate over the existing live portal.

| Check | Expected |
| --- | --- |
| Guest visits business route | Login or denial; no business data |
| Alice/Bob login | Distinct expected identities |
| Own Account/Contact/User route, if required | Only intended fields; no mutation |
| Alice requests Bob's known synthetic record; reverse direction | Denial, no data disclosure |
| Direct Case creation route and applicable API | Denial; verify no Case created |
| Direct approval object/list/detail | Denial |
| Arbitrary business Flow entry | Denial; no side effects |
| Logout then repeat business request | Denial or reauthentication |

For each scenario record date, candidate commit, actor label, operation, expected/actual outcome, evidence reference and pass/fail/not-run. Redact identities and record IDs. UI hiding, static metadata checks and successful dry-run are not runtime access evidence. Do not enable Agentforce until the separate trusted-channel and verified-action gates are met.
