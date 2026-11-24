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
