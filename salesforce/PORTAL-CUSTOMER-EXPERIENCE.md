# Aurora customer experience candidate

This increment changes only the exported ExperienceBundle template. No deployment, publication, profile grants, navigation menu metadata, customer login or Agentforce channel configuration is performed.

## First increment

- Portuguese Aurora after-sales welcome and SEO copy; explicitly states that the authenticated assistant is not available yet.
- Removes community question, discussion/feed, recommendation, leaderboard, trending-topic and support footer components from the home view.
- Removes the shared theme search component and disables the profile-menu contact-support shortcut and messages; hides the app launcher.
- Blue and navy branding using existing branding keys.
- Retains home route, view and region identifiers, existing theme layout and login regions.

These are UI reductions, not authorization controls. Other standard routes, global navigation, direct URLs and APIs remain in the bundle. Audit profile CRUD/FLS, sharing, guest permissions, navigation and direct record/Case access before enabling a customer-facing channel. Do not connect the legacy agent.

## Validation gates

1. Run portal validator, quality gate and CI.
2. Render and run Salesforce metadata dry-run against the development org.
3. Review the actual Experience Builder preview in an isolated configuration; empty regions and theme changes need platform validation. Do not deploy over the live site without an explicit change plan.
4. Verify two distinct external users, guest denial, cross-account denial and logout before attaching any authenticated messaging channel.

Future increments: permission audit, reproducible customer provisioning, navigation minimization, authenticated messaging and trusted runtime identity evidence.

## Remaining route inventory

[portal-route-inventory.json](portal-route-inventory.json) records the 55 route filenames from the candidate Git tree. A regression test checks the exact inventory (normalizing Unicode filenames to NFC). This is not an effective-access report. Prioritize direct Case creation/support, generic record creation and detail/list pages, flows/OmniScript, user/profile/account management, files, reports/dashboards and collaboration routes in the external-profile audit. Retain login, password recovery and error routes until their dependencies and behavior are validated.

## Validation evidence — November 24, 2026

Revision `726fecbc5805872d9727593ff6a340f76b32944b`: local macOS quality gate succeeded (166 tests, 95.25% configured coverage, Mypy clean across 34 files). All three GitHub Actions workflows succeeded. Bandit scanned src only; dependency audit found no known vulnerabilities among audited dependencies (the local project was excluded). The Starlette test client emitted a non-blocking deprecation warning.

Existing Developer Edition: read-only customer reconciliation matched both synthetic customers, distinct account/contact/user identities, active portal users and expected profile; zero mutations. Static validation: 117 JSON files, 55 routes; rendered integrity verified. Salesforce API 68.0 dry-run succeeded, 3/3 components, 67.16 seconds; tests and source tracking skipped. No permanent deployment, visual preview, effective permissions or runtime isolation verified.
