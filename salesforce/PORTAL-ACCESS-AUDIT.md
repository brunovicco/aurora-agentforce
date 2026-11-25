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

## Read-only customer reconciliation

From the repository root, run `bash scripts/sf-audit-portal-customers.sh aurora-dev` against the existing synthetic development org. The query uses fixed synthetic account names and returns only labels and reconciliation statuses to the terminal. Raw query JSON is stored in a private temporary directory and removed on exit. The script does not create or update records, assign permissions, verify passwords or establish session isolation. Missing, duplicate or mismatched users are blockers; review manually before provisioning. This is the first stage of the provisioning harness, not an account creation utility.

## Offline permission evidence reviewer

Run `uv run python scripts/portal_permission_review.py /private/path/evidence.json` against manually normalized evidence. Each of the three synthetic actors supplies `groups_present`, `sources_complete`, and `object_grants` (rows with object, read, create, update, delete, view_all, modify_all; all flags boolean). Include grants from profile-owned permission sets and direct assignments. Group-derived grants and muting require separate resolution. No absence of a grant proves denial. This tool does not collect Salesforce data or inspect FLS, sharing, system permissions or effective group access. Never include IDs or credentials.

## Read-only grant collection candidate

Run `bash scripts/sf-audit-portal-grants.sh aurora-dev` from the repository root. Four Salesforce queries collect customer identities, profile-owned permission sets, assignments and selected object permissions. The last query includes other principals' grant rows locally; normalization keeps only matching sources and the temporary raw files are deleted. Output contains synthetic labels only. Query compatibility and completeness must be validated in the org. The collector always marks source inventories incomplete, leaves guest collection unresolved, and flags groups for separate review. Positive grants may need group muting review. It does not resolve FLS, system permissions, sharing or runtime access, and does not modify Salesforce. A successful exit means report generation, not security approval.

## First grant collection evidence — November 24, 2026

Revision `c0c1bc62cf93e286bc0d286e68899b5fe5891947`: all four Salesforce queries and normalization completed in the existing development org. No disallowed object grants were observed in supplied customer rows. Both customer source inventories remain incomplete by design; guest inventory and group resolution remain outstanding. Effective permissions and runtime access remain unverified; zero mutations. Local tests: 183 passed, configured coverage 95.58% (collector itself not yet included), strict typing clean, Bandit zero findings across 1,282 lines including portal scripts, dependency audit no known vulnerabilities among audited packages. Ruff identified formatting/import issues corrected in the next revision.

## Site guest collection

The revised collector queries the exact Site name and checks its GuestUser relationship against GuestUserId and UserType. It includes profile-owned permission sets and guest assignments in local queries, but only the selected site's guest and the two synthetic customers enter the report. Missing or ambiguous site identity fails closed. Query compatibility remains to be checked in the org. Source completeness, group muting, FLS, system grants and sharing remain unverified.
